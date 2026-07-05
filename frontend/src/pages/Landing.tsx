import { ArrowRight, Zap, Shield, Server } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from '@/components/ui/Button'

export default function Landing() {
  return (
    <div className="flex-1 flex flex-col items-center overflow-hidden relative">
      {/* Background gradients */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[500px] bg-primary/20 blur-[120px] rounded-full pointer-events-none" />

      {/* Hero Section */}
      <section className="py-24 px-6 text-center max-w-5xl mx-auto relative z-10 w-full mt-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <Zap className="w-4 h-4" />
          <span>VMAF 0.6.1 Optimization Engine</span>
        </div>
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 animate-in fade-in slide-in-from-bottom-5 duration-700 delay-100">
          Deliver <span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">Flawless Video</span><br className="hidden md:block"/> at Half the Cost.
        </h1>
        <p className="text-lg md:text-xl text-slate-400 mb-12 max-w-2xl mx-auto leading-relaxed animate-in fade-in slide-in-from-bottom-6 duration-700 delay-200">
          Stop guessing your bitrate. Our API uses Netflix's VMAF model to binary-search the exact compression level your video needs for perfect perceptual quality.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-300">
          <Link to="/auth" className="w-full sm:w-auto">
            <Button className="w-full sm:w-auto text-lg px-8 h-14 rounded-xl gap-2 shadow-xl shadow-primary/25 hover:shadow-primary/40 transition-all group">
              Start Free Trial <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
          <Link to="/docs" className="w-full sm:w-auto">
            <Button variant="secondary" className="w-full sm:w-auto text-lg px-8 h-14 rounded-xl">
              View Documentation
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 w-full bg-slate-900/40 border-t border-slate-800/60 mt-12">
        <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-3 gap-12">
          <div className="space-y-4 group">
            <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform">
              <Zap className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-bold">Lightning Fast Parallel Encoding</h3>
            <p className="text-slate-400 leading-relaxed">
              We split your multi-hour videos into chunks and encode them concurrently across huge CPU clusters. What takes hours locally takes minutes here.
            </p>
          </div>
          <div className="space-y-4 group">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
              <Server className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-bold">VMAF Binary Search</h3>
            <p className="text-slate-400 leading-relaxed">
              Instead of guessing a CRF, we sample your video and search for the exact compression sweet spot that guarantees a 94+ VMAF score.
            </p>
          </div>
          <div className="space-y-4 group">
            <div className="w-14 h-14 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400 group-hover:scale-110 transition-transform">
              <Shield className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-bold">Enterprise Ready API</h3>
            <p className="text-slate-400 leading-relaxed">
              Drop our API directly into your transcoding pipeline. Fully documented, SSRF protected, highly available, and instantly scalable.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
