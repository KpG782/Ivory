<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Ivory | Quote Confirmation</title>
<!-- Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&amp;family=Inter:wght@400;500;600&amp;display=swap" rel="stylesheet"/>
<!-- Material Symbols -->
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
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
        },
      }
    </script>
<style>
        body { font-family: 'Inter', sans-serif; }
        h1, h2, h3, .font-headline { font-family: 'Manrope', sans-serif; }
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .soft-focus-shadow {
            box-shadow: 0 12px 32px -4px rgba(19, 27, 46, 0.06);
        }
        .ai-bubble-shape {
            border-radius: 1.5rem 1.5rem 1.5rem 0.25rem;
        }
        .glass-panel {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(12px);
        }
    </style>
</head>
<body class="bg-surface text-on-surface">
<!-- TopNavBar -->
<header class="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center px-6 py-3 w-full max-w-full sticky top-0 z-50">
<div class="flex items-center gap-4">
<span class="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Ivory</span>
</div>
<nav class="hidden md:flex items-center space-x-8">
<a class="text-slate-500 dark:text-slate-400 hover:text-slate-900 text-sm font-medium transition-colors" href="#">Home</a>
<a class="text-blue-700 dark:text-blue-400 font-semibold border-b-2 border-blue-700 text-sm py-1" href="#">Dashboard</a>
<a class="text-slate-500 dark:text-slate-400 hover:text-slate-900 text-sm font-medium transition-colors" href="#">Support</a>
</nav>
<div class="flex items-center gap-4">
<button class="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-all active:opacity-80 scale-95">
<span class="material-symbols-outlined">notifications</span>
</button>
<button class="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-all active:opacity-80 scale-95">
<span class="material-symbols-outlined">settings</span>
</button>
<div class="w-8 h-8 rounded-full overflow-hidden border border-slate-200">
<img alt="User Profile" class="w-full h-full object-cover" data-alt="professional portrait of a confident man in a suit with a neutral background, soft studio lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBHK7cmNpqLkPtT4Gq47CDRR0RUPsulUew1LDS_39Faq32Ymj5bkPtGDEum0_8vy5rD_k5OCDhOz9zNuz1HSWBmThFEX0-DPGV9WZDTFgw0v8o3BKgeU1Y2kRu7I_DnNkf9LcfNYoHykUe-XnCL6SvVHTMqjdnaQpWqvsbkIGb6hurR6N2tYuU0nhs9Qn0jA2kHDiLlZ5ZmDVgAhKxdoITrNmL4M-szDBOPdRclHpwnCF4Mg5vElQNCWQeZ2veBXalP96qAyXu--sNY"/>
</div>
</div>
</header>
<div class="flex min-h-[calc(100vh-64px)]">
<!-- SideNavBar -->
<aside class="fixed left-0 top-16 h-[calc(100vh-64px)] w-64 bg-slate-50 dark:bg-slate-950 flex flex-col p-4 border-r border-slate-200/50 hidden md:flex">
<div class="mb-8 px-2">
<h2 class="text-lg font-bold text-slate-900 dark:text-slate-50">Guardian History</h2>
<p class="text-xs text-slate-500">Your recent insights</p>
</div>
<nav class="flex-1 space-y-1">
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 px-4 py-2 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 transition-all rounded-lg" href="#">
<span class="material-symbols-outlined text-sm">history</span>
<span class="text-sm font-medium">Recent Quotes</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 px-4 py-2 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 transition-all rounded-lg" href="#">
<span class="material-symbols-outlined text-sm">home_work</span>
<span class="text-sm font-medium">Property Audit</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 px-4 py-2 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 transition-all rounded-lg" href="#">
<span class="material-symbols-outlined text-sm">directions_car</span>
<span class="text-sm font-medium">Vehicle Check</span>
</a>
<a class="flex items-center gap-3 text-slate-500 dark:text-slate-400 px-4 py-2 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 transition-all rounded-lg" href="#">
<span class="material-symbols-outlined text-sm">description</span>
<span class="text-sm font-medium">Policy History</span>
</a>
<a class="flex items-center gap-3 bg-white dark:bg-slate-800 text-blue-700 dark:text-blue-300 font-bold px-4 py-2 rounded-lg shadow-sm" href="#">
<span class="material-symbols-outlined text-sm">smart_toy</span>
<span class="text-sm font-medium">AI Assistant</span>
</a>
</nav>
<div class="mt-auto space-y-1 pt-4 border-t border-slate-200/50">
<a class="flex items-center gap-3 text-slate-500 px-4 py-2 hover:bg-slate-200 rounded-lg" href="#">
<span class="material-symbols-outlined text-sm">settings</span>
<span class="text-sm">Settings</span>
</a>
<a class="flex items-center gap-3 text-slate-500 px-4 py-2 hover:bg-slate-200 rounded-lg" href="#">
<span class="material-symbols-outlined text-sm">help</span>
<span class="text-sm">Help Center</span>
</a>
</div>
</aside>
<!-- Main Content Area -->
<main class="flex-1 md:ml-64 p-6 md:p-12 max-w-5xl mx-auto">
<!-- Breadcrumbs / Mode Indicator -->
<div class="mb-8 flex items-center justify-between">
<div class="flex items-center space-x-2 text-on-surface-variant">
<span class="text-xs font-label tracking-wider uppercase">Auto Quote</span>
<span class="material-symbols-outlined text-sm">chevron_right</span>
<span class="text-xs font-label tracking-wider uppercase font-bold text-secondary">Final Confirmation</span>
</div>
<div class="flex items-center gap-2 px-3 py-1 bg-secondary-fixed rounded-full">
<span class="w-2 h-2 bg-secondary rounded-full animate-pulse"></span>
<span class="text-[10px] font-bold text-on-secondary-fixed-variant uppercase tracking-widest">AI Transactional Mode</span>
</div>
</div>
<!-- Conversational Stream -->
<div class="space-y-10">
<!-- User Message (Implicit state) -->
<div class="flex justify-end">
<div class="max-w-[80%] border-l-4 border-secondary pl-6 py-2">
<p class="text-on-surface font-body font-medium">Confirm my quote for the 2019 Camry with standard coverage options.</p>
</div>
</div>
<!-- AI Response -->
<div class="flex items-start gap-4">
<div class="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center shrink-0">
<span class="material-symbols-outlined text-on-tertiary-container text-xl" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
</div>
<div class="space-y-6 flex-1">
<div class="bg-surface-container-low ai-bubble-shape p-6 max-w-2xl">
<p class="text-lg leading-relaxed text-on-surface font-body">Great news! I've generated your personalized auto insurance quote based on the details provided.</p>
</div>
<!-- Insurance Quote Summary Card (The "Vault") -->
<div class="soft-focus-shadow rounded-xl overflow-hidden bg-surface-container-lowest border border-outline-variant/15">
<!-- Card Header -->
<div class="bg-surface-container-highest px-8 py-5 flex justify-between items-center">
<div>
<h3 class="text-xl font-headline font-extrabold text-primary-container">Insurance Quote Summary</h3>
<p class="text-sm text-on-surface-variant font-body">Quote ID: SB-9920-XF</p>
</div>
<div class="bg-tertiary-fixed text-on-tertiary-fixed px-4 py-2 rounded-lg font-bold flex items-center gap-2">
<span class="material-symbols-outlined text-sm">verified</span>
                                    Best Value
                                </div>
</div>
<!-- Card Body: Bento Style Details -->
<div class="p-8 grid grid-cols-1 md:grid-cols-3 gap-6">
<!-- Premium Breakdown -->
<div class="md:col-span-1 bg-surface-container-low p-6 rounded-xl flex flex-col justify-center text-center">
<span class="text-sm font-label text-on-surface-variant mb-1">Monthly Premium</span>
<div class="text-5xl font-headline font-extrabold text-secondary">$124.50</div>
<span class="text-xs text-on-surface-variant mt-2 font-body">Taxes and fees included</span>
</div>
<!-- Vehicle and Coverage Info -->
<div class="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">
<div class="space-y-4">
<div class="flex items-center gap-3">
<span class="material-symbols-outlined text-secondary" style="font-variation-settings: 'FILL' 1;">directions_car</span>
<div>
<p class="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold">Vehicle</p>
<p class="text-base font-headline font-bold">2019 Toyota Camry</p>
</div>
</div>
<div class="flex items-center gap-3">
<span class="material-symbols-outlined text-secondary" style="font-variation-settings: 'FILL' 1;">shield</span>
<div>
<p class="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold">Policy Status</p>
<p class="text-base font-headline font-bold">New Policy</p>
</div>
</div>
</div>
<div class="space-y-3">
<p class="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-2">Coverages</p>
<ul class="space-y-2">
<li class="flex justify-between items-center text-sm">
<span class="text-on-surface-variant font-body">Liability</span>
<span class="font-bold text-on-surface">$100k/$300k</span>
</li>
<li class="flex justify-between items-center text-sm">
<span class="text-on-surface-variant font-body">Comprehensive</span>
<span class="font-bold text-on-surface">$500 Ded.</span>
</li>
<li class="flex justify-between items-center text-sm">
<span class="text-on-surface-variant font-body">Collision</span>
<span class="font-bold text-on-surface">$500 Ded.</span>
</li>
</ul>
</div>
</div>
</div>
<!-- Card Footer: Actions -->
<div class="px-8 pb-8 pt-4 flex flex-col md:flex-row gap-4">
<button class="flex-1 bg-gradient-to-br from-secondary to-on-secondary-fixed-variant text-on-secondary font-headline font-bold py-4 px-6 rounded-lg transition-all hover:brightness-110 active:scale-[0.98] flex items-center justify-center gap-2">
                                    Accept &amp; Buy Now
                                    <span class="material-symbols-outlined text-lg">arrow_forward</span>
</button>
<button class="flex-1 border border-outline text-on-surface font-headline font-bold py-4 px-6 rounded-lg hover:bg-surface-container-low transition-all active:scale-[0.98] flex items-center justify-center gap-2">
<span class="material-symbols-outlined text-lg">tune</span>
                                    Adjust Coverage
                                </button>
<button class="px-6 py-4 text-on-surface-variant font-headline font-bold flex items-center justify-center gap-2 hover:text-secondary transition-colors">
<span class="material-symbols-outlined text-lg">headset_mic</span>
                                    Talk to an Agent
                                </button>
</div>
</div>
<!-- Trusted by Badge -->
<div class="flex items-center gap-6 opacity-40 grayscale pt-4">
<span class="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface">Underwritten by Top Tier Carriers</span>
<div class="h-6 w-px bg-outline-variant"></div>
<span class="font-headline font-black text-sm italic tracking-tighter">FIN-SECURE</span>
<span class="font-headline font-black text-sm italic tracking-tighter">GLOBAL-RE</span>
</div>
</div>
</div>
</div>
<!-- Input Placeholder (AI Transactional Mode) -->
<div class="mt-20 sticky bottom-8">
<div class="glass-panel border border-outline-variant/30 p-2 rounded-xl flex items-center gap-2 soft-focus-shadow">
<div class="flex-1 px-4 py-3 text-on-surface-variant font-body">
                        Ask a follow-up question or click "Accept" to finalize...
                    </div>
<button class="bg-secondary-container p-3 rounded-lg text-on-secondary-container hover:brightness-105 transition-all">
<span class="material-symbols-outlined">mic</span>
</button>
<button class="bg-secondary p-3 rounded-lg text-on-secondary hover:brightness-105 transition-all">
<span class="material-symbols-outlined">send</span>
</button>
</div>
</div>
</main>
</div>
</body></html>