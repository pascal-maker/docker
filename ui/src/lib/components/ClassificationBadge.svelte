<script lang="ts">
	import type { DocumentClassification } from '$lib/types';

	export let classification: DocumentClassification;

	const colorMap: Record<DocumentClassification, string> = {
		letter: 'bg-teal-100 text-teal-800',
		receipt: 'bg-green-100 text-green-800',
		invoice: 'bg-amber-100 text-amber-800',
		legal_schedule: 'bg-purple-100 text-purple-800',
		sec_filing: 'bg-blue-100 text-blue-800',
		contract: 'bg-indigo-100 text-indigo-800',
		report: 'bg-orange-100 text-orange-800',
		unknown: 'bg-slate-100 text-slate-600'
	};
</script>

<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide {colorMap[classification]}">
	{classification.replace('_', ' ')}
</span>
