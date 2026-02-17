<script lang="ts">
	import type { DocumentNode } from '$lib/types';
	import TreeNode from './TreeNode.svelte';

	export let node: DocumentNode;
	export let depth = 0;
	// undefined = local control; true/false = forced by parent
	export let forceExpanded: boolean | undefined = undefined;

	const AUTO_EXPAND: string[] = ['document', 'chapter', 'section'];
	let localExpanded = AUTO_EXPAND.includes(node.node_type);

	$: expanded = forceExpanded !== undefined ? forceExpanded : localExpanded;

	const hasChildren = node.children.length > 0;
	const hasContent = !!node.content;
	const isExpandable = hasChildren || hasContent;

	const nodeTypeColors: Record<string, string> = {
		document: 'bg-slate-200 text-slate-700',
		segment: 'bg-slate-100 text-slate-600',
		chapter: 'bg-violet-100 text-violet-700',
		section: 'bg-blue-100 text-blue-700',
		subsection: 'bg-sky-100 text-sky-700',
		paragraph: 'bg-slate-100 text-slate-500',
		heading: 'bg-indigo-100 text-indigo-700',
		list: 'bg-green-100 text-green-700',
		list_item: 'bg-green-50 text-green-600',
		table: 'bg-amber-100 text-amber-700',
		table_row: 'bg-amber-50 text-amber-600',
		table_cell: 'bg-yellow-50 text-yellow-600',
		figure: 'bg-pink-100 text-pink-700',
		blockquote: 'bg-orange-100 text-orange-700',
		signature_block: 'bg-teal-100 text-teal-700',
		page_break: 'bg-slate-100 text-slate-400'
	};

	$: color = nodeTypeColors[node.node_type] ?? 'bg-slate-100 text-slate-500';

	function toggle() {
		if (!isExpandable) return;
		if (forceExpanded !== undefined) {
			// Break out of forced state back to local control
			localExpanded = !forceExpanded;
			forceExpanded = undefined;
		} else {
			localExpanded = !localExpanded;
		}
	}
</script>

<div class="text-sm" style="padding-left: {depth > 0 ? '1rem' : '0'}">
	<button
		class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-slate-50 {!isExpandable ? 'cursor-default' : ''}"
		on:click={toggle}
	>
		<span class="w-4 shrink-0 text-slate-400 text-xs">
			{#if isExpandable}
				{expanded ? '▾' : '▸'}
			{:else}
				·
			{/if}
		</span>

		<span class="shrink-0 rounded px-1.5 py-0.5 text-xs font-mono {color}">
			{node.node_type}
		</span>

		{#if node.title}
			<span class="truncate font-medium text-slate-800">{node.title}</span>
		{/if}

		{#if node.metadata.page_start !== null}
			<span class="ml-auto shrink-0 text-xs text-slate-400">
				p.{node.metadata.page_start}{node.metadata.page_end !== null && node.metadata.page_end !== node.metadata.page_start ? `–${node.metadata.page_end}` : ''}
			</span>
		{/if}
	</button>

	{#if expanded && isExpandable}
		<div class="border-l border-slate-200 ml-3">
			{#if hasContent && !hasChildren}
				<p class="py-1 px-3 text-slate-600 text-xs leading-relaxed">{node.content}</p>
			{/if}
			{#each node.children as child}
				<TreeNode node={child} depth={depth + 1} {forceExpanded} />
			{/each}
		</div>
	{/if}
</div>
