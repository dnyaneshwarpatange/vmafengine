import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { getUserJobs, uploadFreeVideo, getJobStatus } from '../lib/api';
import { Upload, Activity, FileVideo, CheckCircle2, Clock, XCircle, Download, Settings2, CreditCard } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function Dashboard() {
  const { user, token, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<any[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  
  // Customization State
  const [showSettings, setShowSettings] = useState(false);
  const [codec, setCodec] = useState('vp9');
  const [resolution, setResolution] = useState('original');
  const [audioBitrate, setAudioBitrate] = useState('96k');

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!loading && !token) {
      navigate('/auth');
    }
  }, [token, loading, navigate]);

  useEffect(() => {
    if (token) {
      fetchJobs();
    }
  }, [token]);

  const fetchJobs = async () => {
    try {
      const data = await getUserJobs(token!);
      setJobs(data);
    } catch (err) {
      console.error('Failed to fetch jobs', err);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !token) return;
    
    setIsUploading(true);
    setError('');
    
    try {
      const res = await uploadFreeVideo(file, token, 94.0, codec, resolution, audioBitrate);
      pollStatus(res.job_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed");
      setIsUploading(false);
    }
  };

  const pollStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const current = await getJobStatus(id, token!);
        if (current.status === 'completed' || current.status === 'failed') {
          clearInterval(interval);
          setIsUploading(false);
          setFile(null);
          fetchJobs();
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  const handleSubscribe = async (planId: string) => {
    if (!token || !user) return;
    try {
      const res = await fetch(`${API_BASE_URL}/v1/payments/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ email: user.email, plan_id: planId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      
        const options = {
        key: 'rzp_test_T2EVAaCCeuP2F0',
        order_id: data.order_id,
        name: 'VMAF Optimizer',
        description: 'Enterprise Video Compression',
        handler: function () {
          alert('Payment Successful! Refreshing credits...');
          window.location.reload();
        },
        prefill: { email: user.email }
      };
      const rzp = new (window as any).Razorpay(options);
      rzp.open();
    } catch (err: any) {
      alert(err.message || 'Subscription failed');
    }
  };

  if (loading || !user) {
    return <div className="flex-1 flex items-center justify-center">Loading...</div>;
  }

  return (
    <div className="flex-1 p-8 max-w-6xl mx-auto w-full">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-slate-400 mt-1">Welcome back, {user.email}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="bg-slate-900 px-4 py-2 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-sm mr-2">Credits:</span>
            <span className="font-bold text-primary">{user.credits}</span>
          </div>
          <Button variant="secondary" onClick={logout}>Sign Out</Button>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        {/* Upload Widget */}
        <div className="md:col-span-1">
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <h2 className="text-xl font-bold mb-2">Upload Video</h2>
            <p className="text-sm text-slate-400 mb-6">Test the engine or use credits. Admin bypasses all limits.</p>
            
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 hover:border-primary/50 transition-colors bg-slate-950/50 text-center relative">
                <input
                  type="file"
                  accept="video/mp4,video/quicktime"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={isUploading}
                />
                <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                <p className="text-sm text-slate-400 font-medium">
                  {file ? file.name : "Drag & drop or click"}
                </p>
              </div>
              
              
              {/* Advanced Settings Accordion */}
              <div>
                <button 
                  type="button" 
                  onClick={() => setShowSettings(!showSettings)}
                  className="flex items-center gap-2 text-sm text-slate-400 hover:text-primary transition-colors"
                >
                  <Settings2 className="w-4 h-4" />
                  Advanced Settings {showSettings ? '▲' : '▼'}
                </button>
                
                {showSettings && (
                  <div className="mt-4 space-y-3 p-4 bg-slate-950 rounded-xl border border-slate-800 text-sm">
                    <div className="flex flex-col gap-1">
                      <label className="text-slate-400">Codec</label>
                      <select value={codec} onChange={(e) => setCodec(e.target.value)} className="bg-slate-900 border border-slate-700 rounded p-2 text-white">
                        <option value="vp9">VP9 (Web Optimized)</option>
                        <option value="hevc">H.265 / HEVC (Best for Storage)</option>
                        <option value="av1">AV1 (Next-Gen)</option>
                        <option value="h264">H.264 (Maximum Compatibility)</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-slate-400">Resolution</label>
                      <select value={resolution} onChange={(e) => setResolution(e.target.value)} className="bg-slate-900 border border-slate-700 rounded p-2 text-white">
                        <option value="original">Original</option>
                        <option value="8k">8K UHD (4320p)</option>
                        <option value="4k">4K UHD (2160p)</option>
                        <option value="1440p">1440p QHD</option>
                        <option value="1080p">1080p FHD</option>
                        <option value="720p">720p HD</option>
                        <option value="480p">480p SD</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-slate-400">Audio Bitrate</label>
                      <select value={audioBitrate} onChange={(e) => setAudioBitrate(e.target.value)} className="bg-slate-900 border border-slate-700 rounded p-2 text-white">
                        <option value="320k">320 kbps (Studio)</option>
                        <option value="192k">192 kbps (High)</option>
                        <option value="128k">128 kbps (Standard)</option>
                        <option value="96k">96 kbps (Efficient)</option>
                        <option value="muted">Muted (Remove Audio)</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              <Button 
                type="submit"
                disabled={!file || isUploading}
                className="w-full h-12 text-md"
              >
                {isUploading ? (
                  <>Processing... <Activity className="w-4 h-4 ml-2 animate-pulse" /></>
                ) : (
                  'Optimize Video'
                )}
              </Button>
            </form>

            {error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm text-center">
                {error}
              </div>
            )}
          </div>

          {/* Subscription Box */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden mt-8">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-primary" /> Get Credits
            </h2>
            <div className="space-y-4">
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex justify-between items-center hover:border-primary/50 transition-colors cursor-pointer" onClick={() => handleSubscribe('plan_starter_499')}>
                <div>
                  <h3 className="font-bold text-white">Starter Plan</h3>
                  <p className="text-xs text-slate-400">1,000 Credits / month</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-primary">$4.99</p>
                </div>
              </div>
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex justify-between items-center hover:border-primary/50 transition-colors cursor-pointer" onClick={() => handleSubscribe('plan_pro_1999')}>
                <div>
                  <h3 className="font-bold text-white">Pro Plan</h3>
                  <p className="text-xs text-slate-400">10,000 Credits / month</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-primary">$19.99</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Job History */}
        <div className="md:col-span-2">
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl h-full">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Recent Jobs</h2>
              <Button variant="ghost" onClick={fetchJobs}>Refresh</Button>
            </div>

            {jobs.length === 0 ? (
              <div className="text-center text-slate-500 py-12">
                <FileVideo className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p>No jobs found. Upload a video to start.</p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                {jobs.map((job) => (
                  <div key={job.job_id} className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between group hover:border-slate-700 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-slate-900 flex items-center justify-center">
                        {job.status === 'completed' ? <CheckCircle2 className="w-5 h-5 text-green-500" /> :
                         job.status === 'failed' ? <XCircle className="w-5 h-5 text-red-500" /> :
                         <Clock className="w-5 h-5 text-blue-500 animate-pulse" />}
                      </div>
                      <div>
                        <p className="font-medium text-sm font-mono text-slate-300">ID: {job.job_id.split('-')[0]}</p>
                        <p className="text-xs text-slate-500 mt-1 capitalize">{job.status} • Target VMAF: {job.target_vmaf}</p>
                      </div>
                    </div>
                    
                    {job.status === 'completed' && (
                      <div className="text-right flex flex-col items-end gap-2">
                        <div>
                          <p className="text-sm font-medium text-green-400">
                            {job.original_size_mb?.toFixed(1)}MB ➔ {job.optimized_size_mb?.toFixed(1)}MB
                          </p>
                          <p className="text-xs text-slate-400 mt-1">
                            VMAF: {job.sampled_vmaf?.toFixed(1)} | {job.codec?.toUpperCase()} | {job.resolution}
                          </p>
                        </div>
                        <a 
                          href={`${API_BASE_URL}/v1/download/${job.job_id}?token=${token}`}
                          className="flex items-center gap-1 text-xs bg-primary/20 text-primary px-3 py-1.5 rounded-md hover:bg-primary/30 transition-colors font-medium"
                        >
                          <Download className="w-3 h-3" /> Download
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
