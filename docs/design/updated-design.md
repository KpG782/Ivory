<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Architectural Guardian | Ivory Insurance</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&amp;family=Inter:wght@400;500;600&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    "colors": {
                        "secondary": "#0051d5",
                        "on-tertiary-fixed": "#002113",
                        "background": "#f7f9fb",
                        "tertiary-fixed": "#6ffbbe",
                        "on-tertiary-fixed-variant": "#005236",
                        "on-secondary-fixed": "#00174b",
                        "surface-dim": "#d8dadc",
                        "surface-container": "#eceef0",
                        "inverse-surface": "#2d3133",
                        "surface-container-lowest": "#ffffff",
                        "on-primary": "#ffffff",
                        "primary": "#000000",
                        "on-surface": "#191c1e",
                        "secondary-container": "#316bf3",
                        "on-secondary": "#ffffff",
                        "inverse-on-surface": "#eff1f3",
                        "secondary-fixed-dim": "#b4c5ff",
                        "outline": "#76777d",
                        "on-error-container": "#93000a",
                        "tertiary-fixed-dim": "#4edea3",
                        "on-error": "#ffffff",
                        "on-surface-variant": "#45464d",
                        "tertiary": "#000000",
                        "on-primary-container": "#7c839b",
                        "on-secondary-container": "#fefcff",
                        "on-primary-fixed": "#131b2e",
                        "tertiary-container": "#002113",
                        "on-tertiary-container": "#009668",
                        "on-secondary-fixed-variant": "#003ea8",
                        "inverse-primary": "#bec6e0",
                        "error": "#ba1a1a",
                        "on-tertiary": "#ffffff",
                        "on-background": "#191c1e",
                        "secondary-fixed": "#dbe1ff",
                        "error-container": "#ffdad6",
                        "surface-variant": "#e0e3e5",
                        "surface-container-low": "#f2f4f6",
                        "surface-container-high": "#e6e8ea",
                        "surface": "#f7f9fb",
                        "primary-fixed": "#dae2fd",
                        "primary-container": "#131b2e",
                        "surface-tint": "#565e74",
                        "surface-container-highest": "#e0e3e5",
                        "surface-bright": "#f7f9fb",
                        "on-primary-fixed-variant": "#3f465c",
                        "outline-variant": "#c6c6cd",
                        "primary-fixed-dim": "#bec6e0"
                    },
                    "borderRadius": {
                        "DEFAULT": "0.25rem",
                        "lg": "0.5rem",
                        "xl": "0.75rem",
                        "full": "9999px"
                    },
                    "fontFamily": {
                        "headline": ["Manrope"],
                        "body": ["Inter"],
                        "label": ["Inter"]
                    }
                },
            },
        }
    </script>
<style>
        body { font-family: 'Inter', sans-serif; }
        .font-manrope { font-family: 'Manrope', sans-serif; }
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .ai-bubble-round {
            border-radius: 1.5rem 1.5rem 1.5rem 0.25rem;
        }
        .glass-panel {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(12px);
        }
    </style>
</head>
<body class="bg-background text-on-surface flex min-h-screen">
<!-- SideNavBar (Authority: JSON) -->
<aside class="h-screen w-72 hidden md:flex flex-col bg-slate-100 dark:bg-slate-950 fixed left-0 top-0 bottom-0 z-40 border-r border-slate-200/15 dark:border-slate-800/15 transition-all duration-200 ease-in-out font-inter text-sm font-medium">
<div class="p-6">
<div class="flex items-center gap-3 mb-8">
<div class="w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center text-secondary">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">architecture</span>
</div>
<div>
<h2 class="font-manrope font-bold text-slate-900 dark:text-slate-50 leading-none">Guardian AI</h2>
<span class="text-[10px] uppercase tracking-wider text-on-primary-container">Premium Intelligence</span>
</div>
</div>
<nav class="space-y-1">
<!-- Active Item: New Chat -->
<a class="flex items-center gap-3 px-4 py-3 bg-white dark:bg-slate-900 text-blue-700 dark:text-blue-400 font-bold rounded-lg transition-all duration-200 ease-in-out" href="#">
<span class="material-symbols-outlined">add_circle</span>
<span>New Chat</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/30 dark:hover:bg-slate-800/30 rounded-lg transition-all duration-200 ease-in-out" href="#">
<span class="material-symbols-outlined">history</span>
<span>History</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/30 dark:hover:bg-slate-800/30 rounded-lg transition-all duration-200 ease-in-out" href="#">
<span class="material-symbols-outlined">account_balance_wallet</span>
<span>Vault</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/30 dark:hover:bg-slate-800/30 rounded-lg transition-all duration-200 ease-in-out" href="#">
<span class="material-symbols-outlined">architecture</span>
<span>Directives</span>
</a>
</nav>
<div class="mt-8">
<p class="px-4 text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">Recent Quotes</p>
<div class="space-y-1">
<div class="px-4 py-2 hover:bg-slate-200/30 rounded-lg cursor-pointer group">
<p class="text-xs text-on-surface truncate">2019 Toyota Camry Hybrid</p>
<p class="text-[10px] text-outline">Processed 2m ago</p>
</div>
<div class="px-4 py-2 hover:bg-slate-200/30 rounded-lg cursor-pointer group">
<p class="text-xs text-on-surface truncate">Home Policy - 1224 Oak</p>
<p class="text-[10px] text-outline">Active Quote</p>
</div>
</div>
</div>
</div>
<div class="mt-auto p-6 border-t border-slate-200/10">
<button class="w-full py-3 px-4 bg-gradient-to-br from-secondary to-on-secondary-fixed-variant text-white rounded-xl font-manrope font-bold text-sm shadow-lg shadow-blue-900/10 hover:opacity-90 transition-opacity mb-6">
                Upgrade to Pro
            </button>
<div class="space-y-1">
<a class="flex items-center gap-3 px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 rounded-lg" href="#">
<span class="material-symbols-outlined text-lg">settings</span>
<span>Settings</span>
</a>
<a class="flex items-center gap-3 px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 rounded-lg" href="#">
<span class="material-symbols-outlined text-lg">help</span>
<span>Help</span>
</a>
</div>
</div>
</aside>
<!-- Main Canvas -->
<main class="flex-1 md:ml-72 flex flex-col relative h-screen overflow-hidden">
<!-- TopAppBar (Authority: JSON) -->
<header class="bg-slate-50/80 dark:bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50 flex justify-between items-center w-full px-6 py-4 tonal transitions via surface-container-low font-manrope font-semibold">
<div class="flex items-center gap-4">
<span class="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Architectural Guardian</span>
</div>
<div class="flex items-center gap-3">
<button class="p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 transition-colors rounded-lg scale-95 active:opacity-80">
<span class="material-symbols-outlined">history</span>
</button>
<button class="p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 transition-colors rounded-lg scale-95 active:opacity-80">
<span class="material-symbols-outlined">settings</span>
</button>
<div class="w-8 h-8 rounded-full bg-surface-container-highest overflow-hidden">
<img alt="User profile" class="w-full h-full object-cover" data-alt="professional headshot of a mature executive with a confident expression in a high-key studio lighting setting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDfezJXo4vSNdvcFoEEyXeir8HGq_M4AtumE04axB-BS7sT4GM1EGp_qtBXKCnf5TIAHuUQ3DRb9EFhOqFF1mZvAv9eku4bAXm9xqGQbhy4_9k5d8mFQvCv-d4lEzN9mNRWCA_TeudKxepY68yUod-bSMDwJW2jQUiJlmtkEeEHF_rVWYuoIzmtOKyY9F9-4_2kltfkPr_ubWubLKFnTw-CHapRV3SOFoArXIR4ez03AjQXDCxE2r_17cKip_IE8xX-wkyaQP4KJtOP"/>
</div>
</div>
</header>
<!-- Chat Stream -->
<div class="flex-1 overflow-y-auto px-6 py-8 space-y-12">
<!-- AI Message -->
<div class="max-w-4xl mr-auto flex gap-6 group">
<div class="w-10 h-10 shrink-0 flex items-center justify-center bg-primary-container text-secondary rounded-lg self-start mt-1">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">architecture</span>
</div>
<div class="flex-1 space-y-4">
<div class="bg-surface-container-low ai-bubble-round p-6 text-on-surface leading-relaxed font-body">
                        Good morning. I've analyzed your request for the 2019 Toyota Camry. Based on your profile and current market risk assessments, I am finalizing a comprehensive protection strategy. 
                        <br/><br/>
                        While I calibrate the final premiums, you can view the live progress of your quote underwriting below.
                    </div>
<!-- Contextual Widget: Auto Quote Progress (Design System: Tonal Layering) -->
<div class="max-w-md bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/15">
<div class="flex justify-between items-center mb-4">
<div class="flex items-center gap-3">
<span class="material-symbols-outlined text-secondary">directions_car</span>
<span class="font-manrope font-bold text-sm">2019 Toyota Camry</span>
</div>
<span class="text-[10px] font-bold text-on-tertiary-container bg-tertiary-fixed px-2 py-1 rounded-full">LIVE PROCESSING</span>
</div>
<div class="space-y-4">
<div class="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
<div class="bg-secondary h-full w-[72%] rounded-full"></div>
</div>
<div class="flex justify-between text-[11px] font-medium text-on-surface-variant">
<span>Underwriting Risk Assessment</span>
<span>72%</span>
</div>
</div>
<div class="mt-6 pt-6 border-t border-outline-variant/10 flex items-center justify-between">
<div>
<p class="text-[10px] text-outline uppercase tracking-wider">Estimated Monthly</p>
<p class="text-xl font-manrope font-extrabold text-on-surface">$112.40</p>
</div>
<button class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg text-xs font-bold hover:bg-surface-container-highest transition-colors">
                                View Details
                            </button>
</div>
</div>
</div>
</div>
<!-- User Message -->
<div class="max-w-2xl ml-auto flex flex-col items-end gap-2">
<div class="flex items-center gap-3 mb-1">
<span class="text-[10px] font-bold text-outline uppercase tracking-widest">You</span>
<div class="w-2 h-4 bg-secondary rounded-full"></div>
</div>
<div class="text-lg font-manrope font-medium text-on-surface text-right">
                    That looks promising. Does this include the multi-policy discount from my homeowner's insurance?
                </div>
</div>
<!-- AI Message 2 with "Best Value" Card -->
<div class="max-w-4xl mr-auto flex gap-6 group">
<div class="w-10 h-10 shrink-0 flex items-center justify-center bg-primary-container text-secondary rounded-lg self-start mt-1">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">architecture</span>
</div>
<div class="flex-1 space-y-6">
<div class="bg-surface-container-low ai-bubble-round p-6 text-on-surface leading-relaxed font-body">
                        Correct. I have automatically tethered your existing Homeowner Policy (SB-99210) to this quote. The current estimate includes a 15% multi-line reduction. 
                        <br/><br/>
                        Here is the refined Architectural Tier for your review:
                    </div>
<!-- Best Value Card (Design System: Quote Summary) -->
<div class="max-w-sm rounded-xl overflow-hidden shadow-[0_12px_32px_-4px_rgba(15,23,42,0.06)] border border-outline-variant/15">
<div class="bg-surface-container-highest p-4 flex justify-between items-center">
<span class="font-manrope font-extrabold text-xs tracking-tight uppercase">Best Value Selection</span>
<span class="material-symbols-outlined text-secondary text-lg" style="font-variation-settings: 'FILL' 1;">verified</span>
</div>
<div class="bg-surface-container-lowest p-6">
<div class="flex items-baseline gap-1 mb-4">
<span class="text-3xl font-manrope font-extrabold">$94.50</span>
<span class="text-xs text-outline font-medium">/ month</span>
</div>
<ul class="space-y-3 mb-6">
<li class="flex items-center gap-2 text-xs text-on-surface">
<span class="material-symbols-outlined text-on-tertiary-container text-sm">check_circle</span>
                                    Comprehensive &amp; Collision ($500 Ded.)
                                </li>
<li class="flex items-center gap-2 text-xs text-on-surface">
<span class="material-symbols-outlined text-on-tertiary-container text-sm">check_circle</span>
                                    24/7 Guardian Roadside Response
                                </li>
<li class="flex items-center gap-2 text-xs text-on-surface">
<span class="material-symbols-outlined text-on-tertiary-container text-sm">check_circle</span>
                                    Gap Protection Included
                                </li>
</ul>
<button class="w-full py-3 bg-gradient-to-r from-secondary to-on-secondary-fixed-variant text-white font-manrope font-bold rounded-lg text-sm transition-all hover:scale-[1.01] active:scale-95">
                                Secure This Quote
                            </button>
</div>
<div class="bg-tertiary-fixed p-3 text-center">
<span class="text-[10px] font-bold text-on-tertiary-fixed-variant">ANNUAL SAVINGS: $214.00</span>
</div>
</div>
</div>
</div>
</div>
<!-- Chat Input Area (Design System: Input Fields) -->
<div class="p-6 bg-surface-bright border-t border-outline-variant/10">
<div class="max-w-4xl mx-auto relative group">
<!-- pulsing secondary_fixed glow via aura effect simulation -->
<div class="absolute -inset-1 bg-secondary-fixed/30 rounded-2xl blur-lg opacity-0 group-focus-within:opacity-100 transition-opacity"></div>
<div class="relative bg-surface-container-lowest border border-outline-variant/30 rounded-2xl shadow-sm flex items-end p-2 transition-all group-focus-within:border-secondary">
<button class="p-3 text-outline hover:text-secondary transition-colors">
<span class="material-symbols-outlined">add</span>
</button>
<textarea class="flex-1 bg-transparent border-none focus:ring-0 resize-none py-3 px-2 text-on-surface font-body text-sm placeholder:text-outline" placeholder="Ask the Guardian about your coverage..." rows="1"></textarea>
<div class="flex items-center gap-1 p-1">
<button class="p-2 text-outline hover:text-on-surface transition-colors">
<span class="material-symbols-outlined">mic</span>
</button>
<button class="p-2 bg-secondary text-white rounded-xl flex items-center justify-center hover:bg-on-secondary-fixed-variant transition-all active:scale-90 shadow-md">
<span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 1;">send</span>
</button>
</div>
</div>
<p class="mt-3 text-center text-[10px] text-outline font-medium">
                    AI Guardian provides guidance. Specific policy terms are governed by your official Ivory contract.
                </p>
</div>
</div>
</main>
<!-- Mobile Bottom Navigation (Logic: Suppress if Task Focused, but this is a Dashboard level) -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 glass-panel border-t border-outline-variant/10 px-6 py-3 flex justify-between items-center z-50">
<button class="flex flex-col items-center gap-1 text-secondary">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">chat_bubble</span>
<span class="text-[10px] font-bold">Chat</span>
</button>
<button class="flex flex-col items-center gap-1 text-outline">
<span class="material-symbols-outlined">account_balance_wallet</span>
<span class="text-[10px] font-bold">Vault</span>
</button>
<div class="relative -top-6">
<button class="w-14 h-14 bg-secondary rounded-full flex items-center justify-center text-white shadow-xl">
<span class="material-symbols-outlined text-3xl">add</span>
</button>
</div>
<button class="flex flex-col items-center gap-1 text-outline">
<span class="material-symbols-outlined">history</span>
<span class="text-[10px] font-bold">History</span>
</button>
<button class="flex flex-col items-center gap-1 text-outline">
<span class="material-symbols-outlined">person</span>
<span class="text-[10px] font-bold">Profile</span>
</button>
</nav>
</body></html>