<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let loading = false;

	const dispatch = createEventDispatcher<{ select: File }>();

	let dragging = false;
	let inputEl: HTMLInputElement;

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		const file = e.dataTransfer?.files[0];
		if (file) dispatch('select', file);
	}

	function handleChange(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (file) dispatch('select', file);
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	class="flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-16 transition-colors cursor-pointer select-none
		{dragging ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:border-slate-400 hover:bg-slate-100'}"
	on:dragover|preventDefault={() => (dragging = true)}
	on:dragleave={() => (dragging = false)}
	on:drop={handleDrop}
	on:click={() => !loading && inputEl.click()}
>
	{#if loading}
		<div class="h-8 w-8 rounded-full border-4 border-slate-200 border-t-blue-500 animate-spin"></div>
		<p class="text-sm text-slate-500">Uploading…</p>
	{:else}
		<svg class="h-10 w-10 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
			<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
		</svg>
		<div class="text-center">
			<p class="font-medium text-slate-700">Drop a PDF here</p>
			<p class="text-sm text-slate-500">or click to browse</p>
		</div>
	{/if}
</div>

<input
	bind:this={inputEl}
	type="file"
	accept=".pdf,application/pdf"
	class="hidden"
	on:change={handleChange}
/>
