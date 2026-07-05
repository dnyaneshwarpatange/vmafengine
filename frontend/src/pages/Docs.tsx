

export default function Docs() {
  return (
    <div className="flex-1 w-full max-w-7xl mx-auto px-6 py-12">
      <div className="grid lg:grid-cols-2 gap-12 lg:gap-24">
        
        {/* Left Prose Column */}
        <div className="prose prose-invert max-w-none">
          <h1 className="text-4xl font-bold tracking-tight mb-4">API Reference</h1>
          <p className="text-lg text-muted-foreground mb-12">
            Integrate the VMAF Engine into your media pipeline to automatically find the perfect balance between file size and perceptual quality.
          </p>

          <hr className="border-border/50 mb-12" />

          <h2 className="text-2xl font-bold mt-12 mb-4 text-primary">Authentication</h2>
          <p className="text-muted-foreground mb-4">
            Authenticate your API requests by including your secret API key in the <code>X-API-Key</code> header. Do not share this key or expose it in client-side code.
          </p>

          <h2 className="text-2xl font-bold mt-12 mb-4 text-primary">Submit a Video</h2>
          <div className="flex items-center gap-3 mb-4">
            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 font-mono text-sm rounded border border-blue-500/30">POST</span>
            <code className="text-muted-foreground bg-slate-900 px-2 py-1 rounded border border-border">/v1/optimize</code>
          </div>
          <p className="text-muted-foreground mb-6">
            Submit a URL for processing. The engine will download it, perform a binary search for the optimal CRF, encode it to VP9, and upload it to your configured S3 bucket.
          </p>

          <h3 className="text-xl font-semibold mb-4 mt-8">Parameters (JSON)</h3>
          <ul className="space-y-4 list-disc pl-5 text-muted-foreground">
            <li><code className="text-white">input_url</code> <span className="text-xs text-rose-400 font-mono ml-2">string, required</span><br/>Publicly accessible HTTP/HTTPS URL to the source video.</li>
            <li><code className="text-white">target_vmaf</code> <span className="text-xs text-emerald-400 font-mono ml-2">float, optional</span><br/>Target visual quality score (0-100). Default is 94.0.</li>
            <li><code className="text-white">codec</code> <span className="text-xs text-emerald-400 font-mono ml-2">string, optional</span><br/>Target codec (vp9, hevc, h264, av1). Default is vp9.</li>
            <li><code className="text-white">resolution</code> <span className="text-xs text-emerald-400 font-mono ml-2">string, optional</span><br/>Target resolution (original, 8k, 4k, 1440p, 1080p, 720p, 480p). Default is original.</li>
            <li><code className="text-white">audio_bitrate</code> <span className="text-xs text-emerald-400 font-mono ml-2">string, optional</span><br/>Target audio bitrate (320k, 192k, 128k, 96k, muted). Default is 96k.</li>
          </ul>

          <hr className="border-border/50 my-12" />

          <h2 className="text-2xl font-bold mt-12 mb-4 text-primary">Check Job Status</h2>
          <div className="flex items-center gap-3 mb-4">
            <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 font-mono text-sm rounded border border-emerald-500/30">GET</span>
            <code className="text-muted-foreground bg-slate-900 px-2 py-1 rounded border border-border">/v1/status/&#123;job_id&#125;</code>
          </div>
          <p className="text-muted-foreground mb-4">
            Poll this endpoint to get the final S3/local output URL and measured VMAF score. 
            For production workflows, we recommend setting up webhooks instead of polling.
          </p>
        </div>

        {/* Right Code Column (Stripe-style sticky) */}
        <div className="relative">
          <div className="sticky top-24 space-y-8">
            
            <div className="rounded-xl overflow-hidden border border-border/50 bg-[#0d1117] shadow-2xl">
              <div className="flex items-center px-4 py-2 bg-[#161b22] border-b border-border/50">
                <span className="text-xs font-mono text-muted-foreground">Authentication Example</span>
              </div>
              <pre className="p-4 text-sm font-mono text-emerald-300 overflow-x-auto">
{`curl -X GET https://api.vmafengine.com/health \\
  -H "X-API-Key: vmaf_live_xxxxxxxxx"`}
              </pre>
            </div>

            <div className="rounded-xl overflow-hidden border border-border/50 bg-[#0d1117] shadow-2xl">
              <div className="flex items-center px-4 py-2 bg-[#161b22] border-b border-border/50">
                <span className="text-xs font-mono text-muted-foreground">Submit Job Request</span>
              </div>
              <pre className="p-4 text-sm font-mono text-[#79c0ff] overflow-x-auto">
{`curl -X POST https://api.vmafengine.com/v1/optimize \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: vmaf_live_xxxxxxxxx" \\
  -d '{
    "input_url": "https://example.com/raw_video.mp4",
    "target_vmaf": 95.0,
    "codec": "hevc",
    "resolution": "1080p",
    "audio_bitrate": "128k"
  }'`}
              </pre>
            </div>

            <div className="rounded-xl overflow-hidden border border-border/50 bg-[#0d1117] shadow-2xl">
              <div className="flex items-center px-4 py-2 bg-[#161b22] border-b border-border/50">
                <span className="text-xs font-mono text-muted-foreground">Response (JSON)</span>
              </div>
              <pre className="p-4 text-sm font-mono text-[#d2a8ff] overflow-x-auto">
{`{
  "job_id": "d81d1b0d-e46e-4c40-a7ce-c0cbf3bbb4cf",
  "status": "pending",
  "message": "Video is being processed..."
}`}
              </pre>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
