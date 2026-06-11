<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Ivory AI Assistant</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Manrope:wght@600;700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            "colors": {
                    "error": "#ba1a1a",
                    "surface-container-highest": "#e0e3e5",
                    "surface-bright": "#f7f9fb",
                    "on-surface": "#191c1e",
                    "surface-dim": "#d8dadc",
                    "error-container": "#ffdad6",
                    "on-primary-fixed": "#131b2e",
                    "inverse-primary": "#bec6e0",
                    "surface-container-low": "#f2f4f6",
                    "secondary-container": "#316bf3",
                    "on-error-container": "#93000a",
                    "on-tertiary-fixed": "#002113",
                    "primary-fixed": "#dae2fd",
                    "on-tertiary-fixed-variant": "#005236",
                    "tertiary-fixed": "#6ffbbe",
                    "surface-variant": "#e0e3e5",
                    "primary-fixed-dim": "#bec6e0",
                    "tertiary": "#000000",
                    "secondary-fixed": "#dbe1ff",
                    "on-surface-variant": "#45464d",
                    "on-secondary-fixed": "#00174b",
                    "inverse-surface": "#2d3133",
                    "inverse-on-surface": "#eff1f3",
                    "surface-container-lowest": "#ffffff",
                    "secondary": "#0051d5",
                    "on-primary-container": "#7c839b",
                    "surface-container": "#eceef0",
                    "tertiary-container": "#002113",
                    "on-secondary-container": "#fefcff",
                    "on-tertiary-container": "#009668",
                    "on-tertiary": "#ffffff",
                    "on-secondary": "#ffffff",
                    "on-error": "#ffffff",
                    "on-primary-fixed-variant": "#3f465c",
                    "on-secondary-fixed-variant": "#003ea8",
                    "primary-container": "#131b2e",
                    "outline-variant": "#c6c6cd",
                    "surface-container-high": "#e6e8ea",
                    "surface": "#f7f9fb",
                    "surface-tint": "#565e74",
                    "secondary-fixed-dim": "#b4c5ff",
                    "background": "#f7f9fb",
                    "primary": "#000000",
                    "outline": "#76777d",
                    "tertiary-fixed-dim": "#4edea3",
                    "on-primary": "#ffffff",
                    "on-background": "#191c1e"
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
        }
      }
    </script>
<style>
        body { font-family: 'Inter', sans-serif; }
        .font-headline { font-family: 'Manrope', sans-serif; }
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .ai-bubble { border-radius: 0.25rem 0.75rem 0.75rem 0.75rem; }
    </style>
</head>
<body class="bg-surface text-on-surface min-h-screen flex flex-col">
<!-- TopNavBar -->
<nav class="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center px-6 py-3 w-full max-w-full fixed top-0 z-50">
<div class="flex items-center gap-8">
<span class="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-50 font-headline">Ivory</span>
<div class="hidden md:flex gap-6">
<a class="text-slate-500 dark:text-slate-400 hover:text-slate-900 transition-colors text-sm font-medium" href="#">Home</a>
<a class="text-blue-700 dark:text-blue-400 font-semibold border-b-2 border-blue-700 text-sm" href="#">Dashboard</a>
<a class="text-slate-500 dark:text-slate-400 hover:text-slate-900 transition-colors text-sm font-medium" href="#">Support</a>
</div>
</div>
<div class="flex items-center gap-4">
<button class="material-symbols-outlined text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 p-2 rounded-full transition-all">notifications</button>
<button class="material-symbols-outlined text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 p-2 rounded-full transition-all">settings</button>
<img alt="User Profile" class="w-8 h-8 rounded-full border border-slate-200" data-alt="professional headshot of a corporate executive in a light blue shirt with a neutral background" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBonpW0pA5xRrO8aqT1_DHMsztjaVqz9ZvM7ejHEDWEBlC2O3lBBwZYYTiqkUnhpSQyEq5y1ivjBYrcFO8Lgf9nK8FKRKfRIXCS2D9tozS79NS1vicCxDi6EaaDbByopt7cyLJBLe8eJJtFUTOAdqSMN561UjUHKecA-r9DHjoEYHEdXNyceiPzJpGyAFedwjVm5LirGd8wciwLqFdh2oOORGNy-ev-FfPy1uBwLE4MsoHQP18HQX9aXDh4zLRSTWuwgGNLQAD5IatU"/>
</div>
</nav>
<div class="flex flex-1 pt-16">
<!-- SideNavBar -->
<aside class="fixed left-0 top-16 h-[calc(100vh-64px)] w-64 bg-slate-50 dark:bg-slate-950 flex flex-col p-4 border-r border-slate-200/50 hidden lg:flex">
<div class="mb-8 px-4">
<h2 class="text-lg font-bold font-headline text-on-surface">Guardian History</h2>
<p class="text-xs text-on-surface-variant">Your recent insights</p>
</div>
<nav class="flex-1 space-y-1">
<a class="flex items-center gap-3 bg-white dark:bg-slate-800 text-blue-700 dark:text-blue-300 font-bold rounded-lg shadow-sm px-4 py-3 text-sm transition-all scale-95 active:opacity-80" href="#">
<span class="material-symbols-outlined text-[20px]">smart_toy</span>
<span>AI Assistant</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 px-4 py-3 text-sm rounded-lg transition-colors" href="#">
<span class="material-symbols-outlined text-[20px]">home_work</span>
<span>Property Audit</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 px-4 py-3 text-sm rounded-lg transition-colors" href="#">
<span class="material-symbols-outlined text-[20px]">directions_car</span>
<span>Vehicle Check</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 px-4 py-3 text-sm rounded-lg transition-colors" href="#">
<span class="material-symbols-outlined text-[20px]">history</span>
<span>Recent Quotes</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 px-4 py-3 text-sm rounded-lg transition-colors" href="#">
<span class="material-symbols-outlined text-[20px]">description</span>
<span>Policy History</span>
</a>
</nav>
<div class="mt-auto space-y-1 border-t border-slate-200 pt-4">
<button class="w-full bg-secondary text-white py-3 px-4 rounded-xl font-semibold text-sm mb-4 transition-all hover:opacity-90 active:scale-95 shadow-lg shadow-secondary/20">
                    Start New Quote
                </button>
<a class="flex items-center gap-3 text-slate-500 px-4 py-2 text-sm hover:text-slate-900" href="#">
<span class="material-symbols-outlined text-[20px]">settings</span>
<span>Settings</span>
</a>
<a class="flex items-center gap-3 text-slate-500 px-4 py-2 text-sm hover:text-slate-900" href="#">
<span class="material-symbols-outlined text-[20px]">help</span>
<span>Help Center</span>
</a>
</div>
</aside>
<!-- Main Content Area -->
<main class="flex-1 lg:ml-64 flex flex-col relative bg-surface">
<!-- Chat Header (Contextual) -->
<div class="bg-surface/80 backdrop-blur-md px-8 py-4 sticky top-0 z-10 flex justify-between items-center">
<div class="flex items-center gap-3">
<div class="w-2 h-2 rounded-full bg-secondary animate-pulse"></div>
<h1 class="font-headline text-lg font-bold">Auto Insurance Advisor</h1>
</div>
<div class="flex gap-2">
<span class="px-3 py-1 bg-tertiary-container text-on-tertiary-container text-[10px] font-bold tracking-wider rounded-full uppercase">Active Session</span>
</div>
</div>
<!-- Chat History Canvas -->
<div class="flex-1 overflow-y-auto px-6 md:px-12 py-8 space-y-10 max-w-4xl mx-auto w-full">
<!-- Message 1: User -->
<div class="flex flex-col items-end group">
<div class="max-w-[85%] md:max-w-[70%] text-right">
<div class="flex items-center justify-end gap-2 mb-1">
<span class="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">You</span>
</div>
<div class="text-on-surface text-lg font-medium border-r-4 border-secondary pr-4 py-1 leading-relaxed">
                            I need a quote for auto insurance.
                        </div>
</div>
</div>
<!-- Message 2: AI -->
<div class="flex flex-col items-start">
<div class="max-w-[90%] md:max-w-[80%]">
<div class="flex items-center gap-2 mb-2">
<div class="bg-primary-container text-white p-1 rounded">
<span class="material-symbols-outlined text-[14px]">smart_toy</span>
</div>
<span class="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">Ivory AI</span>
</div>
<div class="ai-bubble bg-surface-container-low p-6 text-on-surface leading-relaxed text-[15px] shadow-sm">
                            Sure, I'd be happy to help you with an auto insurance quote! First, could you tell me what kind of vehicle you're looking to insure? (e.g., Year, Make, Model)
                        </div>
</div>
</div>
<!-- Message 3: User -->
<div class="flex flex-col items-end group">
<div class="max-w-[85%] md:max-w-[70%] text-right">
<div class="flex items-center justify-end gap-2 mb-1">
<span class="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">You</span>
</div>
<div class="text-on-surface text-lg font-medium border-r-4 border-secondary pr-4 py-1 leading-relaxed">
                            Wait, what does comprehensive coverage actually include?
                        </div>
</div>
</div>
<!-- Message 4: AI (Detailed Explanation) -->
<div class="flex flex-col items-start">
<div class="max-w-[95%] md:max-w-[85%]">
<div class="flex items-center gap-2 mb-2">
<div class="bg-primary-container text-white p-1 rounded">
<span class="material-symbols-outlined text-[14px]">smart_toy</span>
</div>
<span class="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">Ivory AI</span>
</div>
<div class="ai-bubble bg-surface-container-low p-6 text-on-surface shadow-sm overflow-hidden">
<p class="font-headline font-bold text-lg mb-4 text-primary-container">The Architectural Guide to Comprehensive Coverage</p>
<p class="mb-4 leading-relaxed">Great question! Comprehensive coverage typically helps pay for damage to your vehicle from non-collision events, such as theft, fire, vandalism, or falling objects like tree limbs. It's often required if you're leasing or financing your car.</p>
<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-6">
<div class="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/15 flex items-start gap-3">
<span class="material-symbols-outlined text-on-tertiary-container">security</span>
<div>
<p class="text-xs font-bold uppercase tracking-tight text-on-surface-variant">Theft &amp; Vandalism</p>
<p class="text-sm">Total loss or repair costs covered.</p>
</div>
</div>
<div class="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/15 flex items-start gap-3">
<span class="material-symbols-outlined text-on-tertiary-container">thunderstorm</span>
<div>
<p class="text-xs font-bold uppercase tracking-tight text-on-surface-variant">Nature &amp; Weather</p>
<p class="text-sm">Floods, hail, and storm damage.</p>
</div>
</div>
</div>
<p class="mt-6 text-secondary font-semibold">Should we get back to your quote?</p>
</div>
</div>
</div>
<!-- Spacer for scrolling -->
<div class="h-24"></div>
</div>
<!-- Input Area -->
<div class="sticky bottom-0 p-6 bg-gradient-to-t from-surface via-surface/95 to-transparent">
<div class="max-w-4xl mx-auto relative">
<!-- Interaction Aura -->
<div class="absolute -inset-1 bg-secondary-fixed opacity-20 blur-xl rounded-full"></div>
<div class="relative flex items-center bg-surface-container-lowest rounded-2xl p-2 border border-outline-variant/30 shadow-soft-focus shadow-slate-900/5">
<button class="p-3 text-on-surface-variant hover:text-secondary transition-colors">
<span class="material-symbols-outlined">attach_file</span>
</button>
<input class="flex-1 bg-transparent border-none focus:ring-0 text-on-surface py-3 px-2 placeholder:text-outline font-body" placeholder="Ask a question or provide car details..." type="text"/>
<button class="bg-secondary text-white p-3 rounded-xl hover:opacity-90 transition-all flex items-center justify-center shadow-lg shadow-secondary/10">
<span class="material-symbols-outlined">send</span>
</button>
</div>
<div class="flex justify-center mt-3 gap-6">
<button class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant hover:text-secondary transition-colors flex items-center gap-1">
<span class="material-symbols-outlined text-[14px]">history</span> View Full Transcript
                        </button>
<button class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant hover:text-secondary transition-colors flex items-center gap-1">
<span class="material-symbols-outlined text-[14px]">save</span> Save for Later
                        </button>
</div>
</div>
</div>
</main>
<!-- Right Side: Insight Panel (Desktop Only) -->
<aside class="hidden xl:flex w-80 bg-surface-container-low border-l border-slate-200/50 flex-col p-6 overflow-y-auto">
<h3 class="font-headline font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-6">Quote Summary</h3>
<div class="bg-surface-container-lowest rounded-2xl overflow-hidden shadow-sm border border-outline-variant/10 mb-6">
<div class="bg-surface-container-highest p-4 flex items-center justify-between">
<span class="text-xs font-bold uppercase tracking-tighter">Draft Quote #882</span>
<span class="material-symbols-outlined text-sm">open_in_new</span>
</div>
<div class="p-4 space-y-4">
<div class="flex justify-between items-center">
<span class="text-xs text-on-surface-variant">Vehicle Status</span>
<span class="text-xs font-semibold px-2 py-0.5 bg-secondary-fixed rounded text-on-secondary-fixed">Pending Input</span>
</div>
<div class="flex justify-between items-center">
<span class="text-xs text-on-surface-variant">Selected Plan</span>
<span class="text-xs font-semibold">Essential Guard</span>
</div>
<div class="pt-4 border-t border-outline-variant/10">
<div class="flex justify-between items-baseline">
<span class="text-xs font-bold uppercase">Estimated Monthly</span>
<span class="text-xl font-headline font-extrabold text-on-tertiary-container">$ --.--</span>
</div>
</div>
</div>
</div>
<div class="space-y-4">
<h3 class="font-headline font-bold text-sm uppercase tracking-widest text-on-surface-variant">Contextual Tools</h3>
<button class="w-full text-left p-4 rounded-xl bg-white border border-outline-variant/15 hover:bg-slate-50 transition-colors flex gap-3 items-center">
<span class="material-symbols-outlined text-secondary">calculate</span>
<div>
<p class="text-xs font-bold">Premium Estimator</p>
<p class="text-[10px] text-on-surface-variant">Simulate coverage impact</p>
</div>
</button>
<button class="w-full text-left p-4 rounded-xl bg-white border border-outline-variant/15 hover:bg-slate-50 transition-colors flex gap-3 items-center">
<span class="material-symbols-outlined text-secondary">verified_user</span>
<div>
<p class="text-xs font-bold">Policy Comparison</p>
<p class="text-[10px] text-on-surface-variant">Compare against current provider</p>
</div>
</button>
</div>
<!-- Ad/Promo Section -->
<div class="mt-auto pt-8">
<div class="relative rounded-2xl overflow-hidden aspect-[4/5] group">
<img alt="Insurance Consultant" class="absolute inset-0 object-cover w-full h-full brightness-75 group-hover:scale-105 transition-transform duration-700" data-alt="overhead shot of professional office desk with clean paper documents, designer pen, and a laptop with soft window light" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC-oTWOVBqSGDPmxK8Y4UYQvwYfMdTrT6hbH4bsaJy-v15eSGtzZbc8x4ct40gfZf4Tv35Rm91nk-P5MUH_CPWYf2OCrd0F99HT1m6d1eGsvfVugYEbSDZBDdHjui9DO-qiLgb3OGSewxjuFZV0-qAkMGGnRi8nntbD5KdN5UqdfZwb6bSwbxrMa5kodHCy5Lx_nX-gDAELjz_8b_TsnVNiv170qtrjGfvAfKKkDBHa_wnwjQNubpCN8SzeNi5yUIplSr0pSE3JNusS"/>
<div class="absolute inset-0 bg-gradient-to-t from-primary-container via-transparent to-transparent"></div>
<div class="absolute bottom-0 p-6">
<p class="text-white font-headline font-bold text-lg leading-tight">Need expert human review?</p>
<p class="text-blue-200 text-xs mt-2">Connect with a certified agent in under 2 minutes.</p>
<button class="mt-4 bg-tertiary-fixed text-on-tertiary-fixed px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest">Connect Now</button>
</div>
</div>
</div>
</aside>
</div>
<!-- Mobile Navigation (BottomNavBar) -->
<div class="md:hidden fixed bottom-0 left-0 right-0 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 flex justify-around py-3 px-6 z-50">
<button class="flex flex-col items-center gap-1 text-blue-700">
<span class="material-symbols-outlined">smart_toy</span>
<span class="text-[10px] font-medium">Assistant</span>
</button>
<button class="flex flex-col items-center gap-1 text-slate-400">
<span class="material-symbols-outlined">history</span>
<span class="text-[10px] font-medium">History</span>
</button>
<button class="flex flex-col items-center gap-1 text-slate-400">
<span class="material-symbols-outlined">add_circle</span>
<span class="text-[10px] font-medium">New Quote</span>
</button>
<button class="flex flex-col items-center gap-1 text-slate-400">
<span class="material-symbols-outlined">settings</span>
<span class="text-[10px] font-medium">Settings</span>
</button>
</div>
</body></html>