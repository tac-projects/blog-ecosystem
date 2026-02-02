import React, { useState, useEffect } from 'react';
import { Settings, Save, BarChart3, Globe, Zap, PenTool, Layout, CheckCircle, AlertCircle, Key } from 'lucide-react';
import { Octokit } from "@octokit/rest";

const FactoryDashboard = () => {
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState('');
    const [error, setError] = useState('');

    // Config state
    const [config, setConfig] = useState({
        blogName: '',
        githubRepo: 'tac-projects/blog-ecosystem', // Auto-filled
        niche: '',
        language: 'Français',
        tone: 'Expert'
    });

    const [githubToken, setGithubToken] = useState('');
    const [sha, setSha] = useState(null); // SHA of the file to update it

    const [stats, setStats] = useState({
        articleCount: 12, // Mocked for now, could fetch file count later
        lastPost: '2023-10-27',
        status: 'Active'
    });

    const [password, setPassword] = useState('');
    const [isAuthorized, setIsAuthorized] = useState(false);
    const [passError, setPassError] = useState('');

    const MASTER_PASSWORD = "AutObloG846@!";

    // Check for saved token and password on load
    useEffect(() => {
        const savedToken = localStorage.getItem('gh_token');
        const authFlag = localStorage.getItem('is_auth');

        if (authFlag === 'true') {
            setIsAuthorized(true);
        }

        if (savedToken) {
            setGithubToken(savedToken);
            fetchConfig(savedToken);
        }
    }, [isAuthorized]);

    const handleLogin = (e) => {
        e.preventDefault();
        if (password === MASTER_PASSWORD) {
            localStorage.setItem('is_auth', 'true');
            setIsAuthorized(true);
            setPassError('');
        } else {
            setPassError('Mot de passe incorrect ❌');
        }
    };

    // Helper to decode Base64 (UTF-8 safe)
    const base64Decode = (str) => {
        return decodeURIComponent(atob(str).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
    };

    // Helper to encode Base64 (UTF-8 safe)
    const base64Encode = (str) => {
        return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g,
            function toSolidBytes(match, p1) {
                return String.fromCharCode('0x' + p1);
            }));
    };

    const fetchConfig = async (token) => {
        if (!token) return;
        setLoading(true);
        try {
            const octokit = new Octokit({ auth: token });
            const [owner, repo] = config.githubRepo.split('/');

            const response = await octokit.rest.repos.getContent({
                owner,
                repo,
                path: 'blog_config.json',
            });

            const content = base64Decode(response.data.content);
            setConfig(JSON.parse(content));
            setSha(response.data.sha); // Important for updates
            console.log("Config loaded:", JSON.parse(content));
        } catch (err) {
            console.error("Failed to load config:", err);
            // Don't show error to user immediately, might just be first run
        }
        setLoading(false);
    };

    const handleChange = (e) => {
        setConfig({ ...config, [e.target.name]: e.target.value });
    };

    const handleSave = async (e) => {
        e.preventDefault();
        setLoading(true);
        setSuccess('');
        setError('');

        if (!githubToken) {
            setError('GitHub Token is required to save.');
            setLoading(false);
            return;
        }

        try {
            // Save token for convenience
            localStorage.setItem('gh_token', githubToken);

            const octokit = new Octokit({ auth: githubToken });
            const [owner, repo] = config.githubRepo.split('/');

            // 1. Get current SHA if we don't have it (or to be safe)
            let currentSha = sha;
            try {
                const { data } = await octokit.rest.repos.getContent({
                    owner,
                    repo,
                    path: 'blog_config.json'
                });
                currentSha = data.sha;
            } catch (e) {
                // File might not exist yet
            }

            // 2. Update Configuration
            const jsonContent = JSON.stringify(config, null, 2);
            await octokit.rest.repos.createOrUpdateFileContents({
                owner,
                repo,
                path: 'blog_config.json',
                message: 'chore: update blog configuration via dashboard',
                content: base64Encode(jsonContent),
                sha: currentSha, // Include SHA to update existing file
            });

            setSuccess('Configuration saved to GitHub repository!');
            setSha(currentSha); // It changes after update, but we'd need to re-fetch to be exact.

            // Re-fetch to get new SHA
            const { data } = await octokit.rest.repos.getContent({
                owner, repo, path: 'blog_config.json'
            });
            setSha(data.sha);

        } catch (err) {
            console.error("Error saving config:", err);
            setError(`Error: ${err.message}`);
        }
        setLoading(false);
    };

    if (!isAuthorized) {
        return (
            <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 selection:bg-blue-500/30">
                <div className="max-w-md w-full bg-slate-800/50 backdrop-blur-2xl border border-slate-700/50 p-8 rounded-3xl shadow-2xl relative overflow-hidden">
                    <div className="absolute -top-10 -right-10 w-40 h-40 bg-blue-600/10 rounded-full blur-3xl"></div>

                    <div className="flex flex-col items-center mb-8 relative z-10">
                        <div className="p-4 bg-blue-600 rounded-2xl shadow-lg mb-4">
                            <Key className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Accès Sécurisé</h1>
                        <p className="text-slate-400 text-sm">Veuillez entrer le mot de passe maître.</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-4 relative z-10">
                        <input
                            type="password"
                            autoFocus
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-5 py-4 text-white focus:ring-2 focus:ring-blue-600 outline-none transition-all placeholder-slate-600"
                            placeholder="••••••••••••"
                        />
                        {passError && <p className="text-red-400 text-sm font-medium text-center">{passError}</p>}
                        <button
                            type="submit"
                            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-600/20 transition-all active:scale-95"
                        >
                            Déverrouiller le Dashboard
                        </button>
                    </form>

                    <p className="text-center mt-8 text-slate-500 text-xs tracking-widest uppercase">AutoBlog Factory Pro</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-8 selection:bg-blue-500/30">
            <div className="max-w-6xl mx-auto">

                {/* Header */}
                <header className="flex items-center justify-between mb-12">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
                            <Zap className="w-8 h-8 text-white relative z-10" />
                            <div className="absolute inset-0 bg-blue-600 blur-xl opacity-50 rounded-xl"></div>
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                                AutoBlog Factory
                            </h1>
                            <p className="text-slate-400">Control Center & Orchestrator</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="bg-slate-800/80 backdrop-blur border border-slate-700/50 px-4 py-2 rounded-full flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                            <span className="text-sm font-medium text-emerald-400">System Online</span>
                        </div>
                        <button
                            onClick={() => { localStorage.removeItem('is_auth'); setIsAuthorized(false); }}
                            className="text-xs text-slate-500 hover:text-red-400 transition-colors"
                        >
                            Déconnexion
                        </button>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">


                    {/* Main Configuration Panel */}
                    <div className="lg:col-span-2">
                        <div className="bg-slate-800/40 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                            {/* Decorative gradient blob */}
                            <div className="absolute -top-20 -right-20 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>

                            <div className="flex items-center gap-3 mb-8 relative z-10">
                                <Settings className="w-6 h-6 text-blue-400" />
                                <h2 className="text-xl font-semibold text-white">Blog Configuration</h2>
                            </div>

                            <form onSubmit={handleSave} className="space-y-6 relative z-10">

                                {/* Security Section */}
                                <div className="p-4 rounded-xl bg-blue-900/20 border border-blue-500/30 mb-6">
                                    <label className="block text-sm font-medium text-blue-300 mb-2 flex items-center gap-2">
                                        <Key className="w-4 h-4" /> GitHub Personal Access Token (Required to Save)
                                    </label>
                                    <input
                                        type="password"
                                        value={githubToken}
                                        onChange={(e) => setGithubToken(e.target.value)}
                                        className="w-full bg-slate-900/80 border border-blue-500/30 rounded-lg px-4 py-2 text-white placeholder-slate-600/50 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                        placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                                    />
                                    <p className="text-xs text-blue-400/60 mt-2">
                                        Stored locally in your browser. Needs 'repo' scope.
                                    </p>
                                </div>

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
                                            type="text"
                                            name="githubRepo"
                                            value={config.githubRepo}
                                            readOnly
                                            className="w-full bg-slate-900/30 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-slate-400 cursor-not-allowed"
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

                                <div className="border-t border-slate-700/50 pt-8 flex items-center justify-between">
                                    <div className="hidden md:block text-sm text-slate-500">
                                        Targeting Niche: <span className="text-blue-400 font-medium">{config.niche || 'Not set'}</span>
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={loading}
                                        className="w-full md:w-auto flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3 px-8 rounded-xl shadow-lg shadow-blue-600/20 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                                    >
                                        {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Save className="w-5 h-5" />}
                                        Save Configuration
                                    </button>
                                </div>
                                {success && (
                                    <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20 text-sm font-medium animate-in fade-in slide-in-from-top-2">
                                        <CheckCircle className="w-5 h-5 flex-shrink-0" />
                                        {success}
                                    </div>
                                )}
                                {error && (
                                    <div className="flex items-center gap-2 text-red-400 bg-red-500/10 p-4 rounded-xl border border-red-500/20 text-sm font-medium animate-in fade-in slide-in-from-top-2">
                                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                        {error}
                                    </div>
                                )}
                            </form>
                        </div>
                    </div>

                    {/* Sidebar Stats */}
                    <div className="space-y-6">

                        {/* Stats Card */}
                        <div className="bg-slate-800/40 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-xl">
                            <div className="flex items-center gap-3 mb-6">
                                <BarChart3 className="w-6 h-6 text-emerald-400" />
                                <h2 className="text-xl font-semibold text-white">Live Stats</h2>
                            </div>
                            <div className="space-y-4">
                                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50 hover:border-slate-600 transition-colors">
                                    <div className="text-slate-400 text-sm mb-1 font-medium">Total Articles</div>
                                    <div className="text-3xl font-bold text-white tracking-tight">{stats.articleCount}</div>
                                </div>
                                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50 hover:border-slate-600 transition-colors">
                                    <div className="text-slate-400 text-sm mb-1 font-medium">Last Generated</div>
                                    <div className="text-lg font-medium text-white">{stats.lastPost}</div>
                                </div>
                                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50 hover:border-slate-600 transition-colors">
                                    <div className="text-slate-400 text-sm mb-1 font-medium">Engine Status</div>
                                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-sm font-bold border border-emerald-500/20">
                                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                                        {stats.status}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Quick Actions / Info */}
                        <div className="bg-gradient-to-br from-indigo-900/50 to-purple-900/50 backdrop-blur-xl border border-indigo-500/20 rounded-2xl p-6 shadow-xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity duration-500">
                                <PenTool className="w-32 h-32 transform rotate-12" />
                            </div>
                            <h3 className="text-lg font-semibold text-white mb-2 relative z-10">Next Scheduled Run</h3>
                            <p className="text-indigo-200 text-sm mb-6 relative z-10">The automation engine will trigger in 04:23:00</p>
                            <button
                                onClick={async () => {
                                    if (!githubToken) return alert("Token manquant !");
                                    if (!confirm("Lancer la génération d'un article maintenant ?")) return;
                                    try {
                                        const octokit = new Octokit({ auth: githubToken });
                                        const [owner, repo] = config.githubRepo.split('/');
                                        console.log("Triggering workflow:", { owner, repo, workflow_id: 'main.yml' });

                                        await octokit.rest.actions.createWorkflowDispatch({
                                            owner,
                                            repo,
                                            workflow_id: 'main.yml',
                                            ref: 'main'
                                        });
                                        alert("🚀 Robot lancé ! L'article arrivera dans ~2 minutes.");
                                    } catch (e) {
                                        console.error("Workflow trigger failed:", e);
                                        alert("Erreur : " + e.message + (e.status ? ` (Status: ${e.status})` : ""));
                                    }
                                }}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 relative z-10">
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
