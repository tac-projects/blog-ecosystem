import React, { useState, useEffect } from 'react';
import { Settings, Save, BarChart3, Globe, Zap, PenTool, Layout, CheckCircle, AlertCircle } from 'lucide-react';
import { db } from './lib/firebase';
import { doc, setDoc, getDoc } from 'firebase/firestore';

const FactoryDashboard = () => {
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState('');
    const [config, setConfig] = useState({
        blogName: '',
        githubRepo: '',
        niche: '',
        language: 'Français',
        tone: 'Expert'
    });

    const [stats, setStats] = useState({
        articleCount: 12,
        lastPost: '2023-10-27',
        status: 'Active'
    });

    const handleChange = (e) => {
        setConfig({ ...config, [e.target.name]: e.target.value });
    };

    const handleSave = async (e) => {
        e.preventDefault();
        setLoading(true);
        setSuccess('');
        try {
            // Simulation of saving if Firebase config is invalid
            if (db.app.options.apiKey === "YOUR_API_KEY") {
                await new Promise(resolve => setTimeout(resolve, 1000));
                console.warn("Firebase not configured. Data not saved to backend.");
            } else {
                await setDoc(doc(db, "settings", "blogConfig"), config);
            }
            setSuccess('Configuration saved successfully!');
        } catch (error) {
            console.error("Error saving config:", error);
            setSuccess('Error: Check console for details (Firebase Config might be missing)');
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-8">
            <div className="max-w-6xl mx-auto">

                {/* Header */}
                <header className="flex items-center justify-between mb-12">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
                            <Zap className="w-8 h-8 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                                AutoBlog Factory
                            </h1>
                            <p className="text-slate-400">Control Center & Orchestrator</p>
                        </div>
                    </div>
                    <div className="bg-slate-800/50 px-4 py-2 rounded-full border border-slate-700 flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                        <span className="text-sm font-medium text-emerald-400">System Online</span>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Main Configuration Panel */}
                    <div className="lg:col-span-2">
                        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-xl">
                            <div className="flex items-center gap-3 mb-6">
                                <Settings className="w-6 h-6 text-blue-400" />
                                <h2 className="text-xl font-semibold text-white">Blog Configuration</h2>
                            </div>

                            <form onSubmit={handleSave} className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-400 mb-2">Blog Name</label>
                                        <input
                                            type="text"
                                            name="blogName"
                                            value={config.blogName}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder-slate-600"
                                            placeholder="My Awesome Tech Blog"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-400 mb-2">Algorithm Niche</label>
                                        <input
                                            type="text"
                                            name="niche"
                                            value={config.niche}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all placeholder-slate-600"
                                            placeholder="e.g. Artificial Intelligence, Keto Diet"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-400 mb-2">GitHub Repository URL</label>
                                    <div className="relative">
                                        <Globe className="absolute left-3 top-3.5 w-5 h-5 text-slate-500" />
                                        <input
                                            type="url"
                                            name="githubRepo"
                                            value={config.githubRepo}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder-slate-600"
                                            placeholder="https://github.com/username/my-blog-repo"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-400 mb-2">Content Language</label>
                                        <select
                                            name="language"
                                            value={config.language}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                        >
                                            <option>Français</option>
                                            <option>English</option>
                                            <option>Español</option>
                                            <option>Deutsch</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-400 mb-2">AI Tone</label>
                                        <select
                                            name="tone"
                                            value={config.tone}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                        >
                                            <option>Expert</option>
                                            <option>Casual</option>
                                            <option>Journalistic</option>
                                            <option>Humorous</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="border-t border-slate-700 pt-6 flex items-center justify-between">
                                    <div className="text-sm text-slate-500">
                                        Targeting Niche: <span className="text-blue-400 font-medium">{config.niche || 'Not set'}</span>
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={loading}
                                        className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium py-2.5 px-6 rounded-lg shadow-lg shadow-blue-600/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Save className="w-5 h-5" />}
                                        Save Configuration
                                    </button>
                                </div>
                                {success && (
                                    <div className="flex items-center gap-2 text-emerald-400 bg-emerald-400/10 p-3 rounded-lg border border-emerald-400/20 text-sm">
                                        <CheckCircle className="w-4 h-4" />
                                        {success}
                                    </div>
                                )}
                            </form>
                        </div>
                    </div>

                    {/* Sidebar Stats */}
                    <div className="space-y-6">

                        {/* Stats Card */}
                        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-xl">
                            <div className="flex items-center gap-3 mb-6">
                                <BarChart3 className="w-6 h-6 text-emerald-400" />
                                <h2 className="text-xl font-semibold text-white">Live Stats</h2>
                            </div>
                            <div className="space-y-4">
                                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                                    <div className="text-slate-400 text-sm mb-1">Total Articles</div>
                                    <div className="text-2xl font-bold text-white">{stats.articleCount}</div>
                                </div>
                                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                                    <div className="text-slate-400 text-sm mb-1">Last Generated</div>
                                    <div className="text-lg font-medium text-white">{stats.lastPost}</div>
                                </div>
                                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                                    <div className="text-slate-400 text-sm mb-1">Engine Status</div>
                                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-sm font-medium">
                                        <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
                                        {stats.status}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Quick Actions / Info */}
                        <div className="bg-gradient-to-br from-indigo-900/50 to-purple-900/50 backdrop-blur-xl border border-indigo-700/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10">
                                <PenTool className="w-24 h-24" />
                            </div>
                            <h3 className="text-lg font-semibold text-white mb-2">Next Scheduled Run</h3>
                            <p className="text-slate-300 text-sm mb-4">The automation engine will trigger in 04:23:00</p>
                            <button className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors">
                                Trigger Manually
                            </button>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

export default FactoryDashboard;
