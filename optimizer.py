# optimizer.py
"""
VMAF-driven video quality optimizer (Lightning Fast Parallel Algorithm).

1. Binary-searches CRF values on a single short segment for max speed.
2. Slices the source video into 60s chunks (without re-encoding).
3. Encodes all chunks in parallel using Python multiprocessing.
4. Concatenates the chunks perfectly back together.
"""
import subprocess
import json
import os
import random
import shutil
import tempfile
import logging
import glob

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 1200  # seconds

def get_video_duration(video_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return float(json.loads(result.stdout)["format"]["duration"])

def get_video_resolution(video_path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-select_streams", "v:0", "-show_entries", "stream=width,height", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])

def extract_segment(video_path, start_time, duration, output_path):
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_time), "-i", video_path,
        "-t", str(duration), "-c", "copy", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"segment extraction failed: {result.stderr.decode(errors='ignore')[-500:]}")

def calculate_vmaf(original_path, distorted_path, vmaf_log_path):
    width, height = get_video_resolution(original_path)
    resolution = f"{width}x{height}"
    
    threads = os.cpu_count() or 4

    cmd = [
        "ffmpeg", "-i", distorted_path, "-i", original_path,
        "-lavfi",
        f"[0:v]scale={resolution}:flags=bicubic[dist];"
        f"[1:v]scale={resolution}:flags=bicubic[ref];"
        f"[dist][ref]libvmaf=model=version=vmaf_v0.6.1:log_path={vmaf_log_path}:log_fmt=json:n_threads={threads}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"libvmaf run failed: {result.stderr.decode(errors='ignore')[-500:]}")

    with open(vmaf_log_path, "r") as f:
        vmaf_data = json.load(f)
    return vmaf_data["pooled_metrics"]["vmaf"]["mean"]

def build_ffmpeg_cmd(input_path, output_path, crf, codec, resolution, audio_bitrate, is_profiling=False):
    cmd = ["ffmpeg", "-y", "-i", input_path]
    
    # Resolution scaling
    res_map = {
        "8k": "scale=-2:4320",
        "4k": "scale=-2:2160",
        "1440p": "scale=-2:1440",
        "1080p": "scale=-2:1080",
        "720p": "scale=-2:720",
        "480p": "scale=-2:480",
    }
    vf = res_map.get(resolution.lower())
    if vf:
        cmd.extend(["-vf", vf])
        
    # Video Codec
    if codec == "h264":
        preset = "ultrafast" if is_profiling else "fast"
        cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", preset])
    elif codec == "hevc":
        preset = "ultrafast" if is_profiling else "fast"
        cmd.extend(["-c:v", "libx265", "-crf", str(crf), "-preset", preset])
    elif codec == "av1":
        preset = "12" if is_profiling else "8"
        cmd.extend(["-c:v", "libsvtav1", "-crf", str(crf), "-preset", preset])
    else: # default vp9
        speed = "8" if is_profiling else "6"
        cmd.extend([
            "-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0", 
            "-row-mt", "1", "-cpu-used", speed, "-g", "240", 
            "-tile-columns", "4", "-tile-rows", "2"
        ])
        
    # Audio
    if is_profiling or audio_bitrate.lower() == "muted":
        cmd.append("-an")
    else:
        acodec = "aac" if codec in ("h264", "hevc", "av1") else "libopus"
        cmd.extend(["-c:a", acodec, "-b:a", audio_bitrate])
        
    cmd.append(output_path)
    return cmd


def find_optimal_crf(video_path, work_dir, target_vmaf, codec, resolution):
    """
    Minimizes compute: Tests only ONE 2-second segment using the Secant Method.
    """
    duration = get_video_duration(video_path)
    segment_len = min(2, max(1, duration))

    start = random.uniform(0, max(0, duration - segment_len))
    seg_path = os.path.join(work_dir, "seg.mp4")
    extract_segment(video_path, start, segment_len, seg_path)

    # Codec CRF Bounds
    max_crf = 51 if codec in ("h264", "hevc") else 63
    
    # Secant Method State
    x0, x1 = 20.0, 35.0
    f0, f1 = None, None
    best_crf = int(x0)
    best_vmaf = 0

    def evaluate_crf(crf_val):
        nonlocal best_crf, best_vmaf
        crf_int = max(0, min(max_crf, int(round(crf_val))))
        
        encoded_seg = os.path.join(work_dir, f"encoded_{crf_int}.mp4")
        vmaf_log = os.path.join(work_dir, f"vmaf_{crf_int}.json")
        
        cmd = build_ffmpeg_cmd(seg_path, encoded_seg, crf_int, codec, resolution, "muted", is_profiling=True)
        result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(f"segment encode failed: {result.stderr.decode(errors='ignore')[-500:]}")
            
        avg_vmaf = calculate_vmaf(seg_path, encoded_seg, vmaf_log)
        logger.info("Secant Eval: CRF %s -> VMAF %.2f (Target %.2f)", crf_int, avg_vmaf, target_vmaf)
        
        # Track the closest one that meets the target
        if avg_vmaf >= target_vmaf and (best_vmaf == 0 or crf_int > best_crf):
            best_crf, best_vmaf = crf_int, avg_vmaf
        elif best_vmaf == 0: # fallback
            best_crf, best_vmaf = crf_int, avg_vmaf
            
        return crf_int, avg_vmaf - target_vmaf

    # First iteration
    x0, f0 = evaluate_crf(x0)
    if abs(f0) < 0.5: return int(x0), f0 + target_vmaf
    
    x1, f1 = evaluate_crf(x1)
    
    # Secant Loop (Max 5 iterations)
    for _ in range(5):
        if abs(f1) < 0.5 or f1 == f0:
            break
            
        # x_new = x1 - f1 * (x1 - x0) / (f1 - f0)
        x_new = x1 - f1 * (x1 - x0) / (f1 - f0)
        x_new = max(0, min(max_crf, x_new))
        
        if int(round(x_new)) == int(round(x1)) or int(round(x_new)) == int(round(x0)):
            break # converged to same integer
            
        x0, f0 = x1, f1
        x1, f1 = evaluate_crf(x_new)

    return best_crf, best_vmaf


def encode_chunk(args):
    input_chunk, output_chunk, crf, codec, resolution, audio_bitrate = args
    cmd = build_ffmpeg_cmd(input_chunk, output_chunk, crf, codec, resolution, audio_bitrate, is_profiling=False)
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"chunk encode failed: {result.stderr.decode(errors='ignore')[-500:]}")
    return output_chunk


def optimize_video(input_path, output_path, target_vmaf=94.0, codec="vp9", resolution="original", audio_bitrate="96k"):
    work_dir = tempfile.mkdtemp(prefix="vmaf_")
    try:
        optimal_crf, sampled_vmaf = find_optimal_crf(input_path, work_dir, target_vmaf, codec, resolution)
        
        logger.info("Splitting video into 60-second chunks...")
        chunk_pattern = os.path.join(work_dir, "chunk_%04d.mp4")
        split_cmd = [
            "ffmpeg", "-y", "-i", input_path, "-c", "copy",
            "-f", "segment", "-segment_time", "60", "-reset_timestamps", "1",
            chunk_pattern
        ]
        subprocess.run(split_cmd, check=True, capture_output=True)
        
        input_chunks = sorted(glob.glob(os.path.join(work_dir, "chunk_*.mp4")))
        encode_tasks = []
        ext = "mp4" if codec in ("h264", "hevc", "av1") else "webm"
        
        for i, ic in enumerate(input_chunks):
            oc = os.path.join(work_dir, f"out_{i:04d}.{ext}")
            encode_tasks.append((ic, oc, optimal_crf, codec, resolution, audio_bitrate))
            
        max_workers = min(len(input_chunks), os.cpu_count() or 4)
        logger.info(f"Encoding {len(input_chunks)} chunks using {max_workers} parallel workers (Secant CRF: {optimal_crf})...")
        
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            output_chunks = list(pool.map(encode_chunk, encode_tasks))
            
        logger.info("Concatenating chunks...")
        concat_list = os.path.join(work_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for oc in output_chunks:
                f.write(f"file '{oc}'\n")
                
        merge_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", output_path
        ]
        subprocess.run(merge_cmd, check=True, capture_output=True)
        
        return optimal_crf, sampled_vmaf
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
