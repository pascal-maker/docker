<script lang="ts">
	import { uploadPdf, pollJob } from '$lib/api';
	import type { StructuredDocument } from '$lib/types';
	import ClassificationBadge from '$lib/components/ClassificationBadge.svelte';
	import Dropzone from '$lib/components/Dropzone.svelte';
	import TreeNode from '$lib/components/TreeNode.svelte';

	type UIState = 'idle' | 'uploading' | 'polling' | 'done' | 'error';

	let state: UIState = 'idle';
	let stage = '';
	let errorMsg = '';
	let results: StructuredDocument[] = [];
	// per-document forced expansion state: undefined = local control
	let forceExpanded: (boolean | undefined)[] = [];

	async function handleSelect(event: CustomEvent<File>) {
		const file = event.detail;
		state = 'uploading';
		try {
			const jobId = await uploadPdf(file);
			state = 'polling';
			await poll(jobId);
		} catch (e) {
			errorMsg = String(e);
			state = 'error';
		}
	}

	async function poll(jobId: string) {
		while (true) {
			const job = await pollJob(jobId);
			stage = job.stage;
			if (job.status === 'done') {
				results = job.result ?? [];
				forceExpanded = results.map(() => undefined);
				state = 'done';
				return;
			}
			if (job.status === 'error') {
				errorMsg = job.error ?? 'Unknown error';
				state = 'error';
				return;
			}
			await new Promise((r) => setTimeout(r, 2000));
		}
	}

	function reset() {
		state = 'idle';
		results = [];
		forceExpanded = [];
		errorMsg = '';
		stage = '';
	}
</script>

<main class="min-h-screen bg-slate-50 p-8">
	<div class="mx-auto max-w-4xl">
		<header class="mb-8">
			<h1 class="text-2xl font-bold text-slate-900">Document Structuring Agent</h1>
			<p class="mt-1 text-sm text-slate-500">Upload a PDF to extract its hierarchical structure.</p>
		</header>

		{#if state === 'idle' || state === 'uploading'}
			<Dropzone loading={state === 'uploading'} on:select={handleSelect} />

		{:else if state === 'polling'}
			<div class="flex flex-col items-center gap-4 py-24">
				<div class="h-10 w-10 rounded-full border-4 border-slate-200 border-t-blue-500 animate-spin"></div>
				<p class="text-sm font-medium capitalize text-slate-600">{stage}</p>
			</div>

		{:else if state === 'done'}
			<div class="mb-6 flex items-center justify-between">
				<p class="text-sm text-slate-500">{results.length} document{results.length !== 1 ? 's' : ''} found</p>
				<button
					class="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 transition-colors"
					on:click={reset}
				>
					Upload another
				</button>
			</div>

			<div class="flex flex-col gap-6">
				{#each results as doc, i}
					<div class="rounded-xl border border-slate-200 bg-white shadow-sm">
						<div class="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
							<ClassificationBadge classification={doc.classification} />
							<span class="font-medium text-slate-800">{doc.source_filename ?? 'Document'}</span>
							{#if doc.num_pages !== null}
								<span class="text-xs text-slate-400">{doc.num_pages} page{doc.num_pages !== 1 ? 's' : ''}</span>
							{/if}
							<div class="ml-auto flex items-center gap-1">
								<button
									class="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
									on:click={() => { forceExpanded[i] = true; forceExpanded = [...forceExpanded]; }}
								>
									Expand all
								</button>
								<button
									class="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
									on:click={() => { forceExpanded[i] = false; forceExpanded = [...forceExpanded]; }}
								>
									Collapse all
								</button>
							</div>
						</div>
						<div class="p-3">
							<TreeNode node={doc.root} forceExpanded={forceExpanded[i]} />
						</div>
					</div>
				{/each}
			</div>

		{:else if state === 'error'}
			<div class="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
				<p class="mb-4 text-sm text-red-700">{errorMsg}</p>
				<button
					class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
					on:click={reset}
				>
					Try again
				</button>
			</div>
		{/if}
	</div>
</main>
