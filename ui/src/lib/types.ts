export type NodeType =
	| 'document'
	| 'segment'
	| 'chapter'
	| 'section'
	| 'subsection'
	| 'paragraph'
	| 'heading'
	| 'list'
	| 'list_item'
	| 'table'
	| 'table_row'
	| 'table_cell'
	| 'figure'
	| 'blockquote'
	| 'signature_block'
	| 'page_break';

export type DocumentClassification =
	| 'letter'
	| 'receipt'
	| 'invoice'
	| 'legal_schedule'
	| 'sec_filing'
	| 'contract'
	| 'report'
	| 'unknown';

export interface NodeMetadata {
	page_start: number | null;
	page_end: number | null;
	confidence: number | null;
	heading_level: number | null;
}

export interface DocumentNode {
	node_type: NodeType;
	title: string | null;
	content: string | null;
	children: DocumentNode[];
	metadata: NodeMetadata;
}

export interface StructuredDocument {
	root: DocumentNode;
	classification: DocumentClassification;
	source_filename: string | null;
	num_pages: number | null;
}

export type JobStatus = 'queued' | 'processing' | 'done' | 'error';

export interface JobResponse {
	job_id: string;
	status: JobStatus;
	stage: string;
	result?: StructuredDocument[];
	error?: string;
}
