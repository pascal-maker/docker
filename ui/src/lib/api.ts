import type { JobResponse } from '$lib/types';

const BASE = 'http://localhost:8000/api';

export async function uploadPdf(file: File): Promise<string> {
	const form = new FormData();
	form.append('file', file);
	const res = await fetch(`${BASE}/process`, { method: 'POST', body: form });
	if (!res.ok) throw new Error(await res.text());
	const data = await res.json();
	return data.job_id as string;
}

export async function pollJob(jobId: string): Promise<JobResponse> {
	const res = await fetch(`${BASE}/jobs/${jobId}`);
	if (!res.ok) throw new Error(await res.text());
	return res.json() as Promise<JobResponse>;
}
