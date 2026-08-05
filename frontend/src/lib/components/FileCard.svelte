<script>
	import { getFileBlob } from '$lib/api/files.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { fmtBytes, humanize } from '$lib/utils/format.js';

	/**
	 * File card in the files gallery grid. Whole card is a preview trigger;
	 * hover reveals icon actions. Image thumbnails are fetched lazily and the
	 * object URL is revoked when the card is destroyed or the file changes.
	 * @type {{
	 *   file: import('$lib/api/files.js').FileAssetItem,
	 *   canAct: boolean,
	 *   busy?: boolean,
	 *   token: string,
	 *   onpreview: () => void,
	 *   ondownload: () => void,
	 *   onrename: () => void,
	 *   onmove: () => void,
	 *   ondelete: () => void
	 * }}
	 */
	let {
		file,
		canAct,
		busy = false,
		token,
		onpreview,
		ondownload,
		onrename,
		onmove,
		ondelete
	} = $props();

	let isImage = $derived((file.content_type ?? '').toLowerCase().startsWith('image/'));
	let kind = $derived.by(() => {
		const t = (file.content_type ?? '').toLowerCase();
		if (t.startsWith('image/')) return 'image';
		if (t === 'application/pdf') return 'pdf';
		if (t.startsWith('text/')) return 'text';
		return 'file';
	});
	let kindLabel = $derived(
		kind === 'pdf' ? 'PDF' : kind === 'text' ? 'Text' : kind === 'image' ? 'Image' : 'File'
	);

	/**
	 * Non-image cover: show the real file extension (e.g. `zenengr-report.pdf`
	 * → `PDF`). No extension → fall back to the kind label. Truncate at 5
	 * chars for display, keep the full value as the tile `title` tooltip.
	 */
	let extFull = $derived.by(() => {
		const name = file.name ?? '';
		const i = name.lastIndexOf('.');
		if (i < 0 || i === name.length - 1) return kindLabel;
		return name.slice(i + 1).toUpperCase();
	});
	let extShort = $derived(extFull.length > 5 ? extFull.slice(0, 5) : extFull);
	let tileTint = $derived.by(() => {
		const ext = extFull.toLowerCase();
		if (ext === 'pdf') return 'bg-red-50 text-red-700';
		if (ext === 'doc' || ext === 'docx') return 'bg-blue-50 text-blue-700';
		if (ext === 'xls' || ext === 'xlsx' || ext === 'csv') return 'bg-green-50 text-green-700';
		if (ext === 'zip' || ext === 'rar' || ext === '7z' || ext === 'tar' || ext === 'gz')
			return 'bg-amber-50 text-amber-700';
		if (ext === 'text' || ext === 'md' || ext === 'txt' || ext === 'log')
			return 'bg-slate-100 text-slate-700';
		return 'bg-indigo-50 text-indigo-700';
	});

	/** @type {string|null} */
	let thumbUrl = $state(null);
	let thumbLoading = $state(false);

	$effect(() => {
		if (!isImage) {
			thumbUrl = null;
			thumbLoading = false;
			return;
		}
		const id = file.id;
		/** @type {string|null} */
		let url = null;
		let active = true;
		thumbLoading = true;
		getFileBlob(fetch, token, id)
			.then((blob) => {
				if (!active) return;
				url = URL.createObjectURL(blob);
				thumbUrl = url;
				thumbLoading = false;
			})
			.catch(() => {
				if (!active) return;
				thumbLoading = false;
			});
		return () => {
			active = false;
			if (url) {
				URL.revokeObjectURL(url);
				thumbUrl = null;
			}
		};
	});

	/** @param {MouseEvent} e */
	function onClick(e) {
		if (e.target instanceof Element && e.target.closest('button, a')) return;
		onpreview();
	}

	/** @param {KeyboardEvent} e */
	function onKeydown(e) {
		if (e.key !== 'Enter' && e.key !== ' ') return;
		if (e.target instanceof Element && e.target.closest('button, a')) return;
		e.preventDefault();
		onpreview();
	}

	const overlayBtn =
		'flex h-7 w-7 items-center justify-center rounded text-white hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40';
</script>

<div
	class="group relative flex cursor-pointer flex-col rounded-lg border border-slate-200 bg-white p-2 shadow-sm transition focus-within:ring-2 focus-within:ring-indigo-500 focus-within:outline-none hover:border-slate-300 hover:shadow-md"
	role="button"
	tabindex="0"
	aria-label={`Preview ${file.name}`}
	onclick={onClick}
	onkeydown={onKeydown}
>
	<div class="relative">
		<div class="flex h-24 items-center justify-center overflow-hidden rounded-md bg-slate-50">
			{#if thumbUrl}
				<img src={thumbUrl} alt={file.name} class="h-full w-full object-cover" />
			{:else if isImage && thumbLoading}
				<Spinner class="h-6 w-6" />
			{:else}
				{#if kind === 'image'}
					<div class="flex flex-col items-center gap-1 px-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="h-10 w-10 text-slate-400"
							aria-hidden="true"
						>
							<path
								fill-rule="evenodd"
								d="M1 5.25A2.25 2.25 0 013.25 3h13.5A2.25 2.25 0 0119 5.25v9.5A2.25 2.25 0 0116.75 17H3.25A2.25 2.25 0 011 14.75v-9.5zm1.5 5.81v3.69c0 .414.336.75.75.75h13.5a.75.75 0 00.75-.75v-2.69l-2.22-2.219a.75.75 0 00-1.06 0l-1.91 1.91-3.22-3.22a.75.75 0 00-1.06 0L2.5 11.06zm8.5-4.31a1 1 0 112 0 1 1 0 01-2 0z"
								clip-rule="evenodd"
							/>
						</svg>
						<span class="text-xs font-medium tracking-wide text-slate-400 uppercase"
							>{kindLabel}</span
						>
					</div>
				{:else}
					<div
						class="flex h-full w-full flex-col items-center justify-center gap-1 {tileTint}"
						title={extFull}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="h-5 w-5"
							aria-hidden="true"
						>
							<path
								fill-rule="evenodd"
								d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.414a1.5 1.5 0 00-.44-1.06l-3.914-3.914A1.5 1.5 0 0011.586 2H4.5zM6 5.5a.75.75 0 01.75-.75h4.5a.75.75 0 010 1.5h-4.5A.75.75 0 016 5.5zM6.75 9a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zM6 12.25a.75.75 0 01.75-.75h4.5a.75.75 0 010 1.5h-4.5a.75.75 0 01-.75-.75z"
								clip-rule="evenodd"
							/>
						</svg>
						<span class="text-lg font-bold tracking-wide uppercase">{extShort}</span>
					</div>
				{/if}
			{/if}
		</div>
		<div
			class="absolute inset-x-0 bottom-0 flex items-center justify-center gap-1 rounded-b-md bg-slate-900/70 p-2 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 max-sm:opacity-100"
		>
			<button
				type="button"
				title="Preview"
				aria-label="Preview"
				onclick={onpreview}
				class={overlayBtn}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
					<path
						fill-rule="evenodd"
						d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button
				type="button"
				title="Download"
				aria-label="Download"
				onclick={ondownload}
				class={overlayBtn}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75zM3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button
				type="button"
				title="Rename"
				aria-label="Rename"
				disabled={!canAct || busy}
				onclick={onrename}
				class={overlayBtn}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button
				type="button"
				title="Move"
				aria-label="Move"
				disabled={!canAct || busy}
				onclick={onmove}
				class={overlayBtn}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						d="M2 6a2 2 0 012-2h4.586A2 2 0 0110 4.586L11.414 6H16a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"
					/>
				</svg>
			</button>
			<button
				type="button"
				title="Delete"
				aria-label="Delete"
				disabled={!canAct || busy}
				onclick={ondelete}
				class="{overlayBtn} hover:bg-red-500/30 hover:text-red-200"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>
	</div>
	<div class="mt-2 min-w-0 px-1">
		<p class="truncate text-sm font-medium text-slate-900" title={file.name}>{file.name}</p>
		<p class="truncate text-xs text-slate-500">
			{fmtBytes(file.size_bytes)} · {humanize(file.scope)}
		</p>
	</div>
</div>
