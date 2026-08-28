<script>
	import { invalidateAll } from '$app/navigation';
	import { Dialog } from 'bits-ui';
	import { resolve } from '$app/paths';
	import { SvelteMap } from 'svelte/reactivity';
	import { ApiError } from '$lib/api/client.js';
	import * as invoiceApi from '$lib/api/invoices.js';
	import * as projectApi from '$lib/api/projects.js';
	import * as serviceApi from '$lib/api/services.js';
	import AssigneePicker from '$lib/components/AssigneePicker.svelte';
	import CommentThread from '$lib/components/CommentThread.svelte';
	import MilestoneStatusSelector from '$lib/components/MilestoneStatusSelector.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import CopyBadge from '$lib/components/CopyBadge.svelte';
	import ToggleSwitch from '$lib/components/ToggleSwitch.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatAddress } from '$lib/utils/address.js';
	import { formatDate, formatDateTime, fmtPrice, fmtBytes, humanize, formatProjectCode } from '$lib/utils/format.js';
	import * as filesApi from '$lib/api/files.js';
	import FileCard from '$lib/components/FileCard.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Icon from '@iconify/svelte';
	import account from '@iconify-icons/mdi/account';
	import apps from '@iconify-icons/mdi/apps';
	import arrowDown from '@iconify-icons/mdi/arrow-down';
	import arrowUp from '@iconify-icons/mdi/arrow-up';
	import comment from '@iconify-icons/mdi/comment';
	import domain from '@iconify-icons/mdi/domain';
	import emailOutline from '@iconify-icons/mdi/email-outline';
	import fileMultiple from '@iconify-icons/mdi/file-multiple';
	import folderOutline from '@iconify-icons/mdi/folder-outline';
	import mapMarkerOutline from '@iconify-icons/mdi/map-marker-outline';
	import minusCircle from '@iconify-icons/mdi/minus-circle';
	import phoneOutline from '@iconify-icons/mdi/phone-outline';
	import plusCircle from '@iconify-icons/mdi/plus-circle';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import upload from '@iconify-icons/mdi/upload';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';

	let { data } = $props();

	let activeTab = $state('overview');
	let invoiceList = $derived(data.invoices?.items ?? []);
	let issueBusyId = $state(null);
	let pdfBusyId = $state(null);

	// ── Project Files State ──────────────────────────────────────────────────
	let projectFileList = $derived(data.projectFiles ?? []);
	let fileSearchQuery = $state('');
	let fileServiceFilter = $state('all');
	let showFileUploadModal = $state(false);
	let uploadTargetFolderId = $state('');
	let uploadBusy = $state(false);
	/** @type {string|null} */
	let uploadErr = $state(null);
	/** @type {any} */
	let renameTarget = $state(null);
	let newFileName = $state('');
	let renameBusy = $state(false);
	/** @type {string|null} */
	let renameErr = $state(null);
	/** @type {any} */
	let deleteFileTarget = $state(null);
	let deleteFileBusy = $state(false);
	/** @type {any} */
	let previewTarget = $state(null);
	/** @type {string|null} */
	let previewUrl = $state(null);
	let previewLoading = $state(false);

	let projectFolderNodes = $derived.by(() => {
		const roots = Array.isArray(data.folderTree) ? data.folderTree : [];
		const projRoot = roots.find((r) => r.scope === 'project');
		if (!projRoot) return [];
		const thisProjFolder = projRoot.children.find((c) => c.project_id === data.project.id);
		return thisProjFolder ? thisProjFolder.children : [];
	});

	let activeServicesList = $derived(
		(data.project.services ?? []).filter((s) => s.status === 'active')
	);

	let filteredProjectFiles = $derived(
		projectFileList.filter((f) => {
			if (fileSearchQuery.trim()) {
				const q = fileSearchQuery.toLowerCase().trim();
				if (!f.name?.toLowerCase().includes(q)) return false;
			}
			if (fileServiceFilter !== 'all') {
				if (fileServiceFilter === 'general') {
					if (f.folder_id) return false;
				} else {
					if (f.folder_id !== fileServiceFilter) return false;
				}
			}
			return true;
		})
	);

	let uploadTargetChoice = $state('general');
	let isDraggingDropzone = $state(false);

	/** @param {string} [target] */
	function openUploadModal(target = 'general') {
		uploadTargetChoice = target;
		uploadErr = null;
		showFileUploadModal = true;
	}

	/** @param {FileList|File[]} files */
	async function processFilesUpload(files) {
		if (!files || !files.length) return;
		uploadBusy = true;
		uploadErr = null;
		try {
			let targetFolderId = null;

			// If attaching to a specific service
			if (uploadTargetChoice.startsWith('service:')) {
				const svcId = uploadTargetChoice.replace('service:', '');
				const svcName = data.serviceDetails[svcId]?.name || 'Service Deliverables';
				const existing = projectFolderNodes.find((f) => f.name.toLowerCase() === svcName.toLowerCase());
				if (existing) {
					targetFolderId = existing.id;
				} else {
					const roots = Array.isArray(data.folderTree) ? data.folderTree : [];
					const projRoot = roots.find((r) => r.scope === 'project');
					const thisProjFolder = projRoot?.children?.find((c) => c.project_id === data.project.id);
					const newFolder = await filesApi.createFolder(fetch, token, {
						name: svcName,
						scope: 'project',
						project_id: data.project.id,
						parent_id: thisProjFolder?.id || null
					});
					targetFolderId = newFolder.id;
				}
			} else if (uploadTargetChoice.startsWith('folder:')) {
				targetFolderId = uploadTargetChoice.replace('folder:', '');
			}

			for (const file of Array.from(files)) {
				const fd = new FormData();
				fd.append('file', file);
				fd.append('scope', 'project');
				fd.append('project_id', data.project.id);
				if (targetFolderId) {
					fd.append('folder_id', targetFolderId);
				}
				await filesApi.uploadFile(fetch, token, fd);
			}
			showFileUploadModal = false;
			actionMsg = `${files.length} file(s) uploaded successfully.`;
			await invalidateAll();
		} catch (err) {
			uploadErr = err instanceof ApiError ? err.message : 'Upload failed.';
		} finally {
			uploadBusy = false;
			isDraggingDropzone = false;
		}
	}

	/** @param {any} e */
	async function handleFileUpload(e) {
		const files = e.target.files;
		await processFilesUpload(files);
	}

	async function executeFileDelete() {
		if (!deleteFileTarget) return;
		deleteFileBusy = true;
		try {
			await filesApi.deleteFile(fetch, token, deleteFileTarget.id);
			deleteFileTarget = null;
			actionMsg = 'File removed successfully.';
			await invalidateAll();
		} catch (err) {
			actionErr = err instanceof ApiError ? err.message : 'Failed to delete file.';
		} finally {
			deleteFileBusy = false;
		}
	}

	/** @param {any} f */
	function openRenameModal(f) {
		renameTarget = f;
		newFileName = f.name;
		renameErr = null;
	}

	async function executeFileRename() {
		if (!renameTarget || !newFileName.trim()) return;
		renameBusy = true;
		renameErr = null;
		try {
			await filesApi.renameFile(fetch, token, renameTarget.id, { name: newFileName.trim() });
			renameTarget = null;
			await invalidateAll();
		} catch (err) {
			renameErr = err instanceof ApiError ? err.message : 'Failed to rename file.';
		} finally {
			renameBusy = false;
		}
	}

	/** @param {any} f */
	function handleFileDownload(f) {
		filesApi.downloadFile(fetch, token, f.id, f.name);
	}

	/** @param {any} f */
	async function handleFilePreview(f) {
		previewTarget = f;
		previewUrl = null;
		previewLoading = true;
		try {
			const blob = await filesApi.getFileBlob(fetch, token, f.id);
			previewUrl = URL.createObjectURL(blob);
		} catch {
			previewUrl = null;
		} finally {
			previewLoading = false;
		}
	}

	async function issueProjectInvoice(inv) {
		issueBusyId = inv.id;
		actionErr = null;
		try {
			await invoiceApi.issueInvoice(fetch, token, inv.id);
			actionMsg = `Invoice ${inv.invoice_number || ''} issued successfully.`;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not issue invoice.';
		} finally {
			issueBusyId = null;
		}
	}

	async function downloadSingleInvoicePdf(inv) {
		pdfBusyId = inv.id;
		actionErr = null;
		try {
			await invoiceApi.downloadInvoicePdf(fetch, token, inv.id, `${inv.invoice_number || 'invoice'}.pdf`);
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not download invoice PDF.';
		} finally {
			pdfBusyId = null;
		}
	}

	const token = auth.token;

	let canManage = $derived(auth.can('manage', 'projects'));
	let canManageMilestones = $derived(auth.can('manage', 'milestones'));
	let isEmployee = $derived(auth.user?.role === 'employee');

	let actionErr = $state(null);
	let actionMsg = $state(null);
	let statusBusy = $state(false);

	async function changeStatus(next) {
		statusBusy = true;
		actionErr = null;
		actionMsg = null;
		try {
			await projectApi.updateProject(fetch, token, data.project.id, { status: next });
			actionMsg = `Status changed to ${humanize(next)}.`;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Status change failed.';
		} finally {
			statusBusy = false;
		}
	}

	let addOpen = $state(false);
	let addBusy = $state(false);
	let addErr = $state(null);
	let addSelected = $state([]);
	let addPrices = $state({});
	let addPreviewOpen = $state(false);

	let allServices = $state([]);
	let allServiceDetails = $state({});
	let servicesLoading = $state(false);

	let availableToAttach = $derived(
		allServices.filter(
			(s) => !data.project.services.some((ps) => ps.service_id === s.id && ps.status === 'active')
		)
	);

	async function openAddModal() {
		addOpen = true;
		addErr = null;
		addSelected = [];
		addPrices = {};
		addPreviewOpen = false;
		if (allServices.length === 0) {
			servicesLoading = true;
			try {
				const res = await serviceApi.listServices(fetch, token, {
					page_size: 100,
					is_active: true
				});
				allServices = res.items;
			} catch (e) {
				addErr = e instanceof ApiError ? e.message : 'Could not load services.';
			} finally {
				servicesLoading = false;
			}
		}
	}

	$effect(() => {
		if (addOpen && addPreviewOpen && addSelected.length > 0) {
			loadAddPreview();
		}
	});

	async function loadAddPreview() {
		const missing = addSelected.filter((id) => allServiceDetails[id] === undefined);
		if (missing.length === 0) return;
		try {
			const details = await Promise.all(
				missing.map((id) => serviceApi.getService(fetch, token, id))
			);
			const next = { ...allServiceDetails };
			for (const d of details) {
				next[d.id] = (d.steps ?? []).slice().sort((a, b) => a.sequence_order - b.sequence_order);
			}
			allServiceDetails = next;
		} catch (e) {
			addErr = e instanceof ApiError ? e.message : 'Could not load milestone preview.';
		}
	}

	function toggleAddService(svc) {
		if (addSelected.includes(svc.id)) {
			addSelected = addSelected.filter((x) => x !== svc.id);
			const next = { ...addPrices };
			delete next[svc.id];
			addPrices = next;
		} else {
			addSelected = [...addSelected, svc.id];
			addPrices = { ...addPrices, [svc.id]: svc.default_price ?? '' };
		}
	}

	function addPriceError(id) {
		const v = addPrices[id];
		if (v === undefined || v === null || v === '') return null;
		const n = Number(v);
		if (!Number.isFinite(n) || n <= 0) return 'Price must be greater than 0.';
		return null;
	}

	async function confirmAdd() {
		if (addSelected.length === 0) {
			addErr = 'Pick at least one service.';
			return;
		}
		for (const sid of addSelected) {
			if (addPriceError(sid)) {
				addErr = 'Enter a valid price (greater than 0) or clear it to use the default.';
				return;
			}
		}
		addBusy = true;
		addErr = null;
		try {
			for (const sid of addSelected) {
				const body = { service_id: sid };
				const price = addPrices[sid];
				if (price !== undefined && price !== null && price !== '') body.price = price;
				await projectApi.attachService(fetch, token, data.project.id, body);
			}
			addOpen = false;
			await invalidateAll();
		} catch (e) {
			addErr = e instanceof ApiError ? e.message : 'Could not add service.';
		} finally {
			addBusy = false;
		}
	}

	let milestoneBusy = $state({});

	async function patchMilestone(m, patch) {
		milestoneBusy = { ...milestoneBusy, [m.id]: true };
		actionErr = null;
		actionMsg = null;
		try {
			await projectApi.updateMilestone(fetch, token, data.project.id, m.id, patch);
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Update failed.';
		} finally {
			const next = { ...milestoneBusy };
			delete next[m.id];
			milestoneBusy = next;
		}
	}

	let serviceCount = $derived(data.project.services.length);
	let milestoneTotal = $derived(data.project.milestones.length);
	let milestoneCompleted = $derived(
		data.project.milestones.filter((m) => m.status === 'completed').length
	);
	let progressPct = $derived(
		milestoneTotal === 0
			? 0
			: Math.min(100, Math.round((milestoneCompleted / milestoneTotal) * 100))
	);

	let milestonesByService = $derived.by(() => {
		const map = new SvelteMap();
		for (const m of data.project.milestones) {
			const arr = map.get(m.project_service_id) ?? [];
			arr.push(m);
			map.set(m.project_service_id, arr);
		}
		const out = [];
		for (const ps of data.project.services) {
			const items = (map.get(ps.id) ?? [])
				.slice()
				.sort((a, b) => a.sequence_order - b.sequence_order);
			out.push({ key: ps.id, projectService: ps, items });
		}
		return out;
	});

	function fmtDate(d) {
		return d ? formatDate(d) : '—';
	}

	const projectStatusOptions = ['draft', 'active', 'on_hold', 'completed', 'cancelled'];

	let ledgerData = $derived(data.ledger);
	let ledgerEntries = $derived(
		(ledgerData?.entries ?? []).slice().sort((a, b) => {
			const da = a.entry_date ?? a.created_at;
			const db = b.entry_date ?? b.created_at;
			return da < db ? -1 : da > db ? 1 : 0;
		})
	);
	let ledgerSummary = $derived(ledgerData?.summary ?? null);

	function entryMeta(e) {
		const n = Number(e.amount) || 0;
		if (e.type === 'payment') {
			return { icon: arrowDown, text: 'text-green-700', bg: 'bg-green-100' };
		}
		if (e.type === 'refund' || n < 0) {
			return {
				icon: e.type === 'refund' ? arrowUp : minusCircle,
				text: 'text-red-600',
				bg: 'bg-red-100'
			};
		}
		return { icon: plusCircle, text: 'text-slate-600', bg: 'bg-indigo-100' };
	}

	function entryPrice(e) {
		const n = Number(e.amount) || 0;
		const abs = fmtPrice(Math.abs(n));
		if (abs === '—') return '—';
		if (e.type === 'payment') return `+${abs}`;
		if (e.type === 'refund' || n < 0) return `−${abs}`;
		return fmtPrice(n);
	}

	function entryLabel(e) {
		if (e.description) return e.description;
		if (e.source_type === 'manual_adjustment') return 'Manual adjustment';
		return humanize(e.type);
	}

	function entrySubtext(e) {
		if (e.source_type === 'manual_adjustment') return 'Manual adjustment';
		if (e.source_type === 'transaction') return 'Payment';
		return 'Charge';
	}

	let adjustOpen = $state(false);
	let adjustBusy = $state(false);
	let adjustErr = $state(null);
	let adjustAmount = $state('');
	let adjustDescription = $state('');

	function openAdjustDialog() {
		adjustErr = null;
		adjustAmount = '';
		adjustDescription = '';
		adjustOpen = true;
	}

	async function saveAdjustment() {
		adjustErr = null;
		const n = Number(adjustAmount);
		if (adjustAmount === '' || !Number.isFinite(n) || n === 0) {
			adjustErr = 'Enter a non-zero signed amount (negative reduces the total).';
			return;
		}
		if (!adjustDescription.trim()) {
			adjustErr = 'Add a description.';
			return;
		}
		adjustBusy = true;
		try {
			await projectApi.addLedgerAdjustment(fetch, token, data.project.id, {
				amount: String(n),
				description: adjustDescription.trim()
			});
			adjustOpen = false;
			await invalidateAll();
		} catch (e) {
			adjustErr = e instanceof ApiError ? e.message : 'Could not add adjustment.';
		} finally {
			adjustBusy = false;
		}
	}

	let discountOpen = $state(false);
	let discountBusy = $state(false);
	let discountErr = $state(null);
	let discountType = $state('');
	let discountValue = $state('');

	function openDiscountDialog() {
		discountErr = null;
		discountType = ledgerSummary?.discount_type ?? '';
		discountValue = ledgerSummary?.discount_value != null ? ledgerSummary.discount_value : '';
		discountOpen = true;
	}

	async function saveDiscount() {
		discountErr = null;
		const body = { discount_type: null, discount_value: null };
		if (discountType === 'percentage' || discountType === 'fixed') {
			const v = Number(discountValue);
			if (discountValue === '' || !Number.isFinite(v) || v < 0) {
				discountErr = 'Enter a value of 0 or more.';
				return;
			}
			if (discountType === 'percentage' && v > 100) {
				discountErr = 'Percentage must be 100 or less.';
				return;
			}
			body.discount_type = discountType;
			body.discount_value = v;
		}
		discountBusy = true;
		try {
			await projectApi.setProjectDiscount(fetch, token, data.project.id, body);
			discountOpen = false;
			await invalidateAll();
		} catch (e) {
			discountErr = e instanceof ApiError ? e.message : 'Could not save discount.';
		} finally {
			discountBusy = false;
		}
	}

	function discountDisplay() {
		const s = ledgerSummary;
		if (!s?.discount_type) return { display: '—', hint: null };
		const amount = Number(s.discount_amount) || 0;
		const abs = fmtPrice(Math.abs(amount));
		const display = abs === '—' ? '—' : `−${abs}`;
		const hint =
			s.discount_type === 'percentage'
				? `${Math.round((Number(s.discount_value) || 0) * 100) / 100}%`
				: 'fixed';
		return { display, hint };
	}

	let statementOpen = $state(false);
	let statementLoading = $state(false);
	let statementData = $state(null);
	let statementErr = $state(null);
	let statementPdfBusy = $state(false);

	async function openStatementPreview() {
		statementOpen = true;
		statementLoading = true;
		statementErr = null;
		try {
			statementData = await projectApi.getProjectStatement(fetch, token, data.project.id);
		} catch (e) {
			statementErr = e instanceof ApiError ? e.message : 'Could not load project statement.';
		} finally {
			statementLoading = false;
		}
	}

	async function downloadStatementPdf() {
		if (statementPdfBusy) return;
		statementPdfBusy = true;
		statementErr = null;
		try {
			const filename = `statement-${data.project.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.pdf`;
			await projectApi.downloadProjectStatementPdf(fetch, token, data.project.id, filename);
		} catch (e) {
			statementErr = e instanceof ApiError ? e.message : 'Could not download statement PDF.';
		} finally {
			statementPdfBusy = false;
		}
	}

	async function viewStatementPdf() {
		if (statementPdfBusy) return;
		statementPdfBusy = true;
		statementErr = null;
		try {
			await projectApi.viewProjectStatementPdf(fetch, token, data.project.id);
		} catch (e) {
			statementErr = e instanceof ApiError ? e.message : 'Could not view statement PDF.';
		} finally {
			statementPdfBusy = false;
		}
	}

	let generateOpen = $state(false);
	let generateBusy = $state(false);
	let generateErr = $state(null);

	function openGenerateDialog() {
		generateOpen = true;
		generateErr = null;
	}

	async function runGenerateInvoice() {
		generateBusy = true;
		generateErr = null;
		try {
			const inv = await projectApi.generateStatementInvoice(fetch, token, data.project.id);
			generateOpen = false;
			statementOpen = false;
			actionMsg = `Statement invoice ${inv.invoice_number} generated and issued.`;
			await invalidateAll();
		} catch (e) {
			generateErr = e instanceof ApiError ? e.message : 'Could not generate statement invoice.';
		} finally {
			generateBusy = false;
		}
	}

	let paymentOpen = $state(false);
	let paymentBusy = $state(false);
	let paymentErr = $state(null);
	let paymentAmount = $state('');
	let paymentMethod = $state('bank_transfer');
	let paymentDate = $state(new Date().toISOString().slice(0, 10));
	let paymentNote = $state('');

	function openPaymentDialog() {
		paymentErr = null;
		paymentAmount = '';
		paymentMethod = 'bank_transfer';
		paymentDate = new Date().toISOString().slice(0, 10);
		paymentNote = '';
		paymentOpen = true;
	}

	async function savePayment() {
		paymentErr = null;
		const n = Number(paymentAmount);
		if (paymentAmount === '' || !Number.isFinite(n) || n <= 0) {
			paymentErr = 'Enter a valid payment amount greater than 0.';
			return;
		}
		paymentBusy = true;
		try {
			await projectApi.recordProjectPayment(fetch, token, data.project.id, {
				amount: String(n),
				method: paymentMethod,
				entry_date: paymentDate || null,
				reference_note: paymentNote.trim()
			});
			paymentOpen = false;
			actionMsg = 'Payment recorded successfully.';
			await invalidateAll();
		} catch (e) {
			paymentErr = e instanceof ApiError ? e.message : 'Could not record payment.';
		} finally {
			paymentBusy = false;
		}
	}
</script>

<svelte:head><title>{data.project.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/projects')} class="hover:text-indigo-600">Projects</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{data.project.name}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div class="flex items-center gap-3">
		<h1 class="text-2xl font-semibold text-slate-900">{data.project.name}</h1>
		<CopyBadge value={data.project.id} />
		<StatusBadge status={data.project.status} />
	</div>
	{#if canManage}
		<div class="flex flex-wrap items-center gap-2">
			<a
				href={resolve('/app/projects/[id]/edit', { id: data.project.id })}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Edit
			</a>
			<label for="status-select" class="sr-only">Change status</label>
			<select
				id="status-select"
				value={data.project.status}
				disabled={statusBusy}
				aria-busy={statusBusy}
				onchange={(e) => changeStatus(e.currentTarget.value)}
				class="rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#each projectStatusOptions as opt (opt)}
					<option value={opt}>{humanize(opt)}</option>
				{/each}
			</select>
			<button
				type="button"
				disabled
				title="Project deletion is not yet supported in MVP"
				class="cursor-not-allowed rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-400"
			>
				Delete
			</button>
		</div>
	{/if}
</div>

{#if isEmployee}
	<p
		role="status"
		class="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
	>
		View only — contact an admin to make changes.
	</p>
{/if}

{#if actionErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{actionErr}
	</p>
{/if}
{#if actionMsg}
	<p
		role="status"
		class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
	>
		{actionMsg}
	</p>
{/if}

<div class="mt-6 border-b border-slate-200">
	<nav class="-mb-px flex flex-wrap space-x-2 sm:space-x-8" aria-label="Project tabs">
		<button
			type="button"
			onclick={() => (activeTab = 'overview')}
			class="flex items-center gap-2 border-b-2 py-3 px-2 text-sm font-medium {activeTab === 'overview'
				? 'border-indigo-600 text-indigo-600'
				: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
		>
			<Icon icon={viewDashboard} class="h-4 w-4" />
			Overview
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'services')}
			class="flex items-center gap-2 border-b-2 py-3 px-2 text-sm font-medium {activeTab === 'services'
				? 'border-indigo-600 text-indigo-600'
				: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
		>
			<Icon icon={apps} class="h-4 w-4" />
			Services & Milestones
			<span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
				{serviceCount}
			</span>
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'ledger')}
			class="flex items-center gap-2 border-b-2 py-3 px-2 text-sm font-medium {activeTab === 'ledger'
				? 'border-indigo-600 text-indigo-600'
				: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
		>
			<Icon icon={receiptText} class="h-4 w-4" />
			Ledger & Financials
			{#if ledgerSummary}
				{@const adv = Number(ledgerSummary.advance_balance) || 0}
				{@const due = Number(ledgerSummary.due) || 0}
				<span
					class="rounded-full px-2 py-0.5 text-xs font-semibold {adv > 0
						? 'bg-emerald-100 text-emerald-800'
						: due > 0
							? 'bg-amber-100 text-amber-800'
							: 'bg-slate-100 text-slate-600'}"
				>
					{adv > 0 ? `+${fmtPrice(ledgerSummary.advance_balance)}` : fmtPrice(ledgerSummary.due)}
				</span>
			{/if}
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'invoices')}
			class="flex items-center gap-2 border-b-2 py-3 px-2 text-sm font-medium {activeTab === 'invoices'
				? 'border-indigo-600 text-indigo-600'
				: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
		>
			<Icon icon={fileMultiple} class="h-4 w-4" />
			Invoices
			<span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
				{invoiceList.length}
			</span>
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'files')}
			class="flex items-center gap-2 border-b-2 py-3 px-2 text-sm font-medium {activeTab === 'files'
				? 'border-indigo-600 text-indigo-600'
				: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
		>
			<Icon icon={folderOutline} class="h-4 w-4" />
			Files
			<span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
				{projectFileList.length}
			</span>
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'comments')}
			class="flex items-center gap-2 border-b-2 py-3 px-2 text-sm font-medium {activeTab === 'comments'
				? 'border-indigo-600 text-indigo-600'
				: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
		>
			<Icon icon={comment} class="h-4 w-4" />
			Comments
		</button>
	</nav>
</div>

{#if activeTab === 'overview'}
<!-- Overview Tab -->
<div class="mt-6 space-y-6">
	<!-- Client Information Card -->
	<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs" aria-labelledby="client-info-h">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
			<div class="flex items-center gap-3">
				<div class="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
					<Icon icon={account} class="h-6 w-6" />
				</div>
				<div>
					<div class="flex items-center gap-2">
						<h2 id="client-info-h" class="text-base font-semibold text-slate-900">
							{data.client?.name ?? 'Client Information'}
						</h2>
						{#if data.client?.client_type}
							<span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 capitalize">
								{data.client.client_type}
							</span>
						{/if}
						{#if data.client?.status}
							<StatusBadge status={data.client.status} />
						{/if}
					</div>
					<p class="text-xs text-slate-500 mt-0.5">Primary client for this project</p>
				</div>
			</div>

			{#if data.project.client_id}
				<a
					href={resolve('/app/clients/[id]', { id: data.project.client_id })}
					class="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors"
				>
					View Client Profile &rarr;
				</a>
			{/if}
		</div>

		<dl class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<div>
				<dt class="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wider">
					<Icon icon={emailOutline} class="h-3.5 w-3.5 text-slate-400" />
					Email
				</dt>
				<dd class="mt-1 text-sm text-slate-900">
					{#if data.client?.email}
						<a href={`mailto:${data.client.email}`} class="text-indigo-600 hover:underline">
							{data.client.email}
						</a>
					{:else}
						<span class="text-slate-400">&mdash;</span>
					{/if}
				</dd>
			</div>

			<div>
				<dt class="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wider">
					<Icon icon={phoneOutline} class="h-3.5 w-3.5 text-slate-400" />
					Phone
				</dt>
				<dd class="mt-1 text-sm text-slate-900">
					{#if data.client?.phone}
						<a href={`tel:${data.client.phone}`} class="text-slate-700 hover:underline">
							{data.client.phone}
						</a>
					{:else}
						<span class="text-slate-400">&mdash;</span>
					{/if}
				</dd>
			</div>

			<div>
				<dt class="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wider">
					<Icon icon={mapMarkerOutline} class="h-3.5 w-3.5 text-slate-400" />
					Billing Address
				</dt>
				<dd class="mt-1 text-sm text-slate-900">
					{#if data.client?.billing_address && formatAddress(data.client.billing_address)}
						<span>{formatAddress(data.client.billing_address)}</span>
					{:else}
						<span class="text-slate-400">&mdash;</span>
					{/if}
				</dd>
			</div>

			<div>
				<dt class="text-xs font-medium text-slate-500 uppercase tracking-wider">Tags</dt>
				<dd class="mt-1 flex flex-wrap gap-1">
					{#if data.client?.tags && data.client.tags.length > 0}
						{#each data.client.tags as tag (tag)}
							<span class="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
								{tag}
							</span>
						{/each}
					{:else}
						<span class="text-xs text-slate-400">&mdash;</span>
					{/if}
				</dd>
			</div>
		</dl>
	</section>

	<!-- Project Details & Milestones Card -->
	<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs" aria-labelledby="project-details-h">
		<h2 id="project-details-h" class="text-base font-semibold text-slate-900">Project Details</h2>
		<dl class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<div>
				<dt class="text-xs font-medium tracking-wider text-slate-500 uppercase">Start Date</dt>
				<dd class="mt-1 text-sm text-slate-900 font-medium">{fmtDate(data.project.start_date)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wider text-slate-500 uppercase">Target Due Date</dt>
				<dd class="mt-1 text-sm text-slate-900 font-medium">
					{data.project.target_delivery_date ? fmtDate(data.project.target_delivery_date) : '—'}
				</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wider text-slate-500 uppercase">Project Owner</dt>
				<dd class="mt-1 text-sm text-slate-900 font-medium">
					{#if data.project.owner_id}
						{data.users.find((u) => u.id === data.project.owner_id)?.full_name ?? '—'}
					{:else}
						<span class="text-slate-400">Unassigned</span>
					{/if}
				</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wider text-slate-500 uppercase">Active Services</dt>
				<dd class="mt-1 text-sm text-slate-900 font-medium">{data.project.services.length}</dd>
			</div>
		</dl>

		<div class="mt-6 border-t border-slate-100 pt-5">
			<div class="flex items-baseline justify-between">
				<p class="text-xs font-semibold tracking-wider text-slate-600 uppercase">Milestone Progress</p>
				<p class="text-xs font-medium text-slate-700">
					{milestoneCompleted} of {milestoneTotal} completed
					{#if milestoneTotal > 0}
						<span class="font-bold text-indigo-600">({progressPct}%)</span>
					{/if}
				</p>
			</div>
			{#if milestoneTotal > 0}
				<div
					class="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100"
					role="progressbar"
					aria-valuenow={milestoneCompleted}
					aria-valuemin={0}
					aria-valuemax={milestoneTotal}
					aria-label={`Milestone progress for ${data.project.name}`}
				>
					<div class="h-full rounded-full bg-indigo-600 transition-all duration-300" style="width: {progressPct}%"></div>
				</div>
			{:else}
				<p class="mt-2 text-xs text-slate-500">No milestones attached to this project's services yet.</p>
			{/if}
		</div>
	</section>

	<!-- Financial Overview Card -->
	<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs" aria-labelledby="fin-overview-h">
		<div class="flex items-center justify-between border-b border-slate-100 pb-3">
			<h2 id="fin-overview-h" class="text-base font-semibold text-slate-900">Financial Snapshot</h2>
			<button
				type="button"
				onclick={() => (activeTab = 'invoices')}
				class="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
			>
				Go to Invoices ({invoiceList.length}) &rarr;
			</button>
		</div>

		<div class="mt-4 grid gap-4 sm:grid-cols-3">
			<div class="rounded-lg bg-slate-50 p-4 border border-slate-100">
				<dt class="text-xs font-medium tracking-wider text-slate-500 uppercase">Project Total</dt>
				<dd class="mt-1 text-xl font-bold text-slate-900">
					{ledgerSummary ? fmtPrice(ledgerSummary.total) : (data.overview?.financials ? fmtPrice(data.overview.financials.total) : '—')}
				</dd>
			</div>
			<div class="rounded-lg bg-emerald-50/60 p-4 border border-emerald-100">
				<dt class="text-xs font-medium tracking-wider text-emerald-700 uppercase">Total Paid</dt>
				<dd class="mt-1 text-xl font-bold text-emerald-700">
					{ledgerSummary ? fmtPrice(ledgerSummary.paid) : (data.overview?.financials ? fmtPrice(data.overview.financials.paid) : '—')}
				</dd>
			</div>
			<div class="rounded-lg p-4 border {Number(ledgerSummary?.due ?? data.overview?.financials?.due) > 0 ? 'bg-amber-50/60 border-amber-200' : 'bg-slate-50 border-slate-100'}">
				<dt class="text-xs font-medium tracking-wider {Number(ledgerSummary?.due ?? data.overview?.financials?.due) > 0 ? 'text-amber-800' : 'text-slate-500'} uppercase">Outstanding Due</dt>
				<dd class="mt-1 text-xl font-bold {Number(ledgerSummary?.due ?? data.overview?.financials?.due) > 0 ? 'text-amber-800' : 'text-emerald-700'}">
					{ledgerSummary ? fmtPrice(ledgerSummary.due) : (data.overview?.financials ? fmtPrice(data.overview.financials.due) : '—')}
				</dd>
			</div>
		</div>

		{#if Number(ledgerSummary?.advance_balance ?? data.overview?.financials?.advance_balance) > 0}
			<div class="mt-3 rounded-lg bg-indigo-50 p-3 text-xs text-indigo-900 border border-indigo-100 flex items-center justify-between">
				<span>Advance Credit Available:</span>
				<span class="font-bold text-indigo-700 text-sm">{fmtPrice(ledgerSummary?.advance_balance ?? data.overview?.financials?.advance_balance)}</span>
			</div>
		{/if}
	</section>

	<!-- Timestamps -->
	<div class="flex flex-wrap items-center justify-between text-xs text-slate-400 px-1">
		<p>Created {formatDateTime(data.project.created_at)}</p>
		<p>Last updated {formatDateTime(data.project.updated_at)}</p>
	</div>
</div>
{/if}

{#if activeTab === 'services'}
<!-- Services -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="services-h"
>
	<div class="flex items-center justify-between border-b border-slate-200 px-6 py-4">
		<div>
			<h2 id="services-h" class="text-base font-semibold text-slate-900">Services</h2>
			<p class="mt-0.5 text-sm text-slate-500">
				{data.project.services.length}
				{data.project.services.length === 1 ? 'service' : 'services'} attached
			</p>
		</div>
		{#if canManage}
			<button
				type="button"
				onclick={openAddModal}
				class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Add service
			</button>
		{/if}
	</div>

	{#if data.project.services.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No services attached yet.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Service</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Price</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Milestones</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.project.services as ps (ps.id)}
						{@const isCancelled = ps.status === 'cancelled'}
						<tr class={isCancelled ? 'bg-slate-50 text-slate-500' : 'hover:bg-slate-50'}>
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<span class={isCancelled ? 'line-through' : ''}>{ps.service_name}</span>
							</td>
							<td class="px-4 py-3"><StatusBadge status={ps.status} /></td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(ps.price_at_attachment)}</td
							>
							<td class="px-4 py-3 text-right text-sm text-slate-700">
								{data.project.milestones.filter((m) => m.project_service_id === ps.id).length}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<!-- Milestones section -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="milestones-h"
>
	<h2 id="milestones-h" class="text-base font-semibold text-slate-900">Milestones</h2>
	{#if data.project.milestones.length === 0}
		<p class="mt-4 text-sm text-slate-500">No milestones yet.</p>
	{:else}
		<div class="mt-4 space-y-6">
			{#each milestonesByService as group (group.key)}
				{@const isCancelled = group.projectService.status === 'cancelled'}
				<div>
					<div class="flex items-center gap-2">
						<h3
							class="text-sm font-semibold {isCancelled
								? 'text-slate-500 line-through'
								: 'text-slate-900'}"
						>
							{group.projectService.service_name}
						</h3>
						<StatusBadge status={group.projectService.status} />
						<span class="text-xs text-slate-500">
							· {group.items.length}
							{group.items.length === 1 ? 'milestone' : 'milestones'}
						</span>
					</div>

					<ul class="mt-3 divide-y divide-slate-200 rounded-md border border-slate-200">
						{#each group.items as m (m.id)}
							{@const mBusy = Boolean(milestoneBusy[m.id])}
							<li
								class="grid gap-2 px-4 py-3 sm:grid-cols-12 sm:items-center {isCancelled
									? 'bg-slate-50 text-slate-500'
									: ''}"
							>
								<div class="sm:col-span-5">
									<div class="flex items-start gap-2">
										<span
											class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
											aria-hidden="true"
										>
											{m.sequence_order}
										</span>
										<div class="min-w-0">
											<p
												class="text-sm font-medium {isCancelled
													? 'line-through'
													: 'text-slate-900'}"
											>
												{m.name}
											</p>
											{#if m.description}
												<p class="mt-0.5 text-xs text-slate-500">{m.description}</p>
											{/if}
										</div>
									</div>
								</div>
								<div class="sm:col-span-3">
									<MilestoneStatusSelector
										value={m.status}
										busy={mBusy}
										disabled={!canManageMilestones || isCancelled}
										onchange={(next) => patchMilestone(m, { status: next })}
										id={`m-status-${m.id}`}
									/>
								</div>
								<div class="text-xs text-slate-600 sm:col-span-2">
									<p>
										<span class="block text-slate-500">Planned</span>
										{fmtDate(m.planned_date)}
									</p>
									<p class="mt-1">
										<span class="block text-slate-500">Actual</span>
										{fmtDate(m.actual_date)}
									</p>
								</div>
								<div class="sm:col-span-2">
									<AssigneePicker
										value={m.assignee_id}
										users={data.users}
										busy={mBusy}
										disabled={!canManageMilestones || isCancelled}
										onchange={(uid) => patchMilestone(m, { assignee_id: uid })}
										id={`m-assignee-${m.id}`}
									/>
								</div>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
	{/if}
</section>
{/if}

{#if activeTab === 'ledger'}
{#if canManage}
	<div class="mt-6 flex flex-wrap items-center gap-3">
		<button
			type="button"
			onclick={openPaymentDialog}
			class="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
		>
			<Icon icon={arrowDown} class="h-4 w-4" />
			Record payment
		</button>
		<button
			type="button"
			onclick={openStatementPreview}
			class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Preview statement
		</button>
		<button
			type="button"
			onclick={openGenerateDialog}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Generate invoice
		</button>
		<button
			type="button"
			onclick={openAdjustDialog}
			class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Add adjustment
		</button>
		<button
			type="button"
			onclick={openDiscountDialog}
			class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Edit discount
		</button>
		<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
		<a
			href={resolve('/app/invoices/new') + '?project_id=' + data.project.id}
			class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Custom invoice
		</a>
		<!-- eslint-enable svelte/no-navigation-without-resolve -->
	</div>
{/if}

<!-- Ledger balance summary -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="ledger-balance-h"
>
	<h2 id="ledger-balance-h" class="text-base font-semibold text-slate-900">
		Project ledger (balance)
	</h2>
	{#if !ledgerData}
		<p class="mt-4 text-sm text-slate-500">Ledger unavailable.</p>
	{:else}
		{@const disc = discountDisplay()}
		{@const due = Number(ledgerSummary?.due) || 0}
		{@const advanceBal = Number(ledgerSummary?.advance_balance) || 0}
		<dl class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Subtotal</dt>
				<dd class="mt-1 text-lg font-semibold text-slate-900">
					{fmtPrice(ledgerSummary?.subtotal)}
				</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Discount</dt>
				<dd class="mt-1 text-lg font-semibold text-slate-900">
					{disc.display}
					{#if disc.hint}
						<span class="ml-1 text-xs font-normal text-slate-500">({disc.hint})</span>
					{/if}
				</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total</dt>
				<dd class="mt-1 text-lg font-semibold text-slate-900">{fmtPrice(ledgerSummary?.total)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Paid</dt>
				<dd class="mt-1 text-lg font-semibold text-green-700">{fmtPrice(ledgerSummary?.paid)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Due</dt>
				<dd class="mt-1 text-lg font-bold {due > 0 ? 'text-red-600' : 'text-green-700'}">
					{fmtPrice(ledgerSummary?.due)}
				</dd>
			</div>
		</dl>
		{#if advanceBal > 0}
			<div class="mt-4 rounded-md border border-indigo-200 bg-indigo-50 p-3">
				<p class="text-sm font-medium text-indigo-900">
					Client Advance Credit: <span class="font-bold text-indigo-700">{fmtPrice(ledgerSummary?.advance_balance)}</span>
				</p>
				<p class="mt-0.5 text-xs text-indigo-700">
					Payments received exceed current charges. Credit will automatically apply toward future charges.
				</p>
			</div>
		{/if}
	{/if}
</section>

<!-- Ledger -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="ledger-h"
>
	<div
		class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4"
	>
		<div>
			<h2 id="ledger-h" class="text-base font-semibold text-slate-900">Ledger timeline</h2>
			<p class="mt-0.5 text-sm text-slate-500">
				Balance-forward timeline of charges, payments and refunds.
			</p>
		</div>
	</div>

	{#if !ledgerData}
		<p class="px-6 py-8 text-sm text-slate-500">Ledger unavailable.</p>
	{:else if ledgerEntries.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No ledger entries yet.</p>
	{:else}
		<ul class="divide-y divide-slate-100">
			{#each ledgerEntries as e (e.id)}
				{@const meta = entryMeta(e)}
				{@const price = entryPrice(e)}
				<li class="flex items-center gap-3 px-6 py-3">
					<span
						class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full {meta.bg}"
						aria-hidden="true"
					>
						<Icon icon={meta.icon} class="h-4 w-4 {meta.text}" />
					</span>
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-slate-900" title={entryLabel(e)}>
							{entryLabel(e)}
						</p>
						<p class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
							<span>{entrySubtext(e)}</span>
							<span aria-hidden="true">·</span>
							<span>{e.entry_date ? formatDate(e.entry_date) : formatDateTime(e.created_at)}</span>
							{#if e.type === 'charge' && e.invoice_ref && e.invoice_number}
								<a
									href={resolve('/app/invoices/[id]', { id: e.invoice_ref })}
									class="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700 ring-1 ring-indigo-600/20 hover:bg-indigo-100"
								>
									Included in {e.invoice_number}
								</a>
							{/if}
						</p>
					</div>
					<p class="shrink-0 text-sm font-semibold whitespace-nowrap {meta.text}">{price}</p>
				</li>
			{/each}
		</ul>
	{/if}
</section>
{/if}

{#if activeTab === 'invoices'}
<!-- Invoices -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="invoices-tab-h"
>
	<div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4">
		<div>
			<h2 id="invoices-tab-h" class="text-base font-semibold text-slate-900">Project Invoices</h2>
			<p class="mt-0.5 text-sm text-slate-500">
				{invoiceList.length} {invoiceList.length === 1 ? 'invoice' : 'invoices'} issued or drafted for this project
			</p>
		</div>
		{#if canManage}
			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					onclick={openGenerateDialog}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Generate Statement Invoice
				</button>
				<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
				<a
					href={`${resolve('/app/invoices/new')}?project_id=${data.project.id}`}
					class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					New Custom Invoice
				</a>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			</div>
		{/if}
	</div>

	{#if invoiceList.length === 0}
		<div class="px-6 py-12 text-center">
			<p class="text-sm text-slate-500">No invoices generated for this project yet.</p>
			{#if canManage}
				<div class="mt-4 flex flex-wrap justify-center gap-3">
					<button
						type="button"
						onclick={openGenerateDialog}
						class="rounded-md bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
					>
						Generate statement invoice
					</button>
					<!-- eslint-disable svelte/no-navigation-without-resolve -->
					<a
						href={`${resolve('/app/invoices/new')}?project_id=${data.project.id}`}
						class="rounded-md border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
					>
						Create custom invoice
					</a>
					<!-- eslint-enable svelte/no-navigation-without-resolve -->
				</div>
			{/if}
		</div>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th scope="col" class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase">Invoice #</th>
						<th scope="col" class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase">Status</th>
						<th scope="col" class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase">Total</th>
						<th scope="col" class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase">Issue date</th>
						<th scope="col" class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase">Due date</th>
						<th scope="col" class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase">Actions</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each invoiceList as inv (inv.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/invoices/[id]', { id: inv.id })}
									class="font-semibold text-indigo-600 hover:text-indigo-500"
								>
									{inv.invoice_number ? inv.invoice_number : 'Draft'}
								</a>
							</td>
							<td class="px-4 py-3"><StatusBadge status={inv.status} /></td>
							<td class="px-4 py-3 text-right text-sm font-semibold whitespace-nowrap text-slate-900">{fmtPrice(inv.total)}</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600">{formatDate(inv.issue_date)}</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600">{formatDate(inv.due_date)}</td>
							<td class="px-4 py-3 text-right">
								<div class="flex items-center justify-end gap-3 text-sm">
									<a
										href={resolve('/app/invoices/[id]', { id: inv.id })}
										class="font-medium text-indigo-600 hover:text-indigo-500"
									>
										View
									</a>
									{#if inv.status === 'draft' && canManage}
										<button
											type="button"
											disabled={issueBusyId === inv.id}
											onclick={() => issueProjectInvoice(inv)}
											class="font-medium text-emerald-600 hover:text-emerald-500 disabled:opacity-50"
										>
											{#if issueBusyId === inv.id}Issuing...{:else}Issue{/if}
										</button>
									{/if}
									{#if inv.status !== 'draft'}
										<button
											type="button"
											disabled={pdfBusyId === inv.id}
											onclick={() => downloadSingleInvoicePdf(inv)}
											class="font-medium text-slate-600 hover:text-slate-900 disabled:opacity-50"
										>
											{#if pdfBusyId === inv.id}Downloading...{:else}PDF{/if}
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>
{/if}

{#if activeTab === 'files'}
<!-- Project Files -->
<section class="mt-6 space-y-4" aria-labelledby="project-files-h">
	<!-- Control Toolbar -->
	<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
		<div class="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
			<!-- Search Box -->
			<div class="relative flex-1 max-w-sm">
				<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
					<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
				</div>
				<input
					type="text"
					bind:value={fileSearchQuery}
					placeholder="Search project files..."
					class="block w-full rounded-lg border-slate-300 pl-9 pr-8 text-sm placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
				/>
				{#if fileSearchQuery}
					<button
						type="button"
						onclick={() => (fileSearchQuery = '')}
						class="absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-slate-600"
						aria-label="Clear search"
					>
						<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				{/if}
			</div>

			<!-- Filter Selector -->
			<div class="flex items-center gap-2">
				<select
					bind:value={fileServiceFilter}
					class="rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
				>
					<option value="all">All Files ({projectFileList.length})</option>
					<option value="general">General Project Files</option>
					{#if projectFolderNodes.length > 0}
						<optgroup label="Folders & Services">
							{#each projectFolderNodes as fn (fn.id)}
								<option value={fn.id}>📁 {fn.name}</option>
							{/each}
						</optgroup>
					{/if}
				</select>
			</div>
		</div>

		<div>
			<button
				type="button"
				onclick={() => openUploadModal('general')}
				class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-2xs hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
			>
				<Icon icon={upload} class="h-4 w-4" />
				Upload File
			</button>
		</div>
	</div>

	<!-- Files Grid -->
	{#if filteredProjectFiles.length === 0}
		<div class="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-2xs">
			<div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
				<Icon icon={folderOutline} class="h-6 w-6" />
			</div>
			<h3 class="mt-3 text-sm font-semibold text-slate-900">No project files found</h3>
			<p class="mt-1 text-xs text-slate-500">
				{fileSearchQuery || fileServiceFilter !== 'all'
					? 'No files match your current search criteria.'
					: 'Upload design assets, deliverables, contracts, or specifications for this project.'}
			</p>
			{#if fileSearchQuery || fileServiceFilter !== 'all'}
				<div class="mt-4">
					<button
						type="button"
						onclick={() => {
							fileSearchQuery = '';
							fileServiceFilter = 'all';
						}}
						class="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-200"
					>
						Clear filters
					</button>
				</div>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
			{#each filteredProjectFiles as f (f.id)}
				<FileCard
					file={f}
					canAct={true}
					{token}
					onpreview={() => handleFilePreview(f)}
					ondownload={() => handleFileDownload(f)}
					onrename={() => openRenameModal(f)}
					onmove={() => {}}
					ondelete={() => (deleteFileTarget = f)}
				/>
			{/each}
		</div>
	{/if}
</section>
{/if}

{#if activeTab === 'comments'}
<!-- Comments -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="comments-h"
>
	<h2 id="comments-h" class="text-base font-semibold text-slate-900">Comments</h2>
	<div class="mt-2">
		<CommentThread projectId={data.project.id} {fetch} {token} realm="admin" staff={true} />
	</div>
</section>
{/if}

<!-- Add adjustment dialog -->
<Dialog.Root bind:open={adjustOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Add adjustment</Dialog.Title>
				<Dialog.Close
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Signed amount: positive adds to the project total, negative offsets it. The change is
				appended to the ledger and cannot be edited or removed.
			</Dialog.Description>

			{#if adjustErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{adjustErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					saveAdjustment();
				}}
			>
				<div>
					<label for="adjust-amount" class="block text-sm font-medium text-slate-700">Amount</label>
					<input
						id="adjust-amount"
						type="number"
						step="0.01"
						placeholder="0.00"
						bind:value={adjustAmount}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="adjust-desc" class="block text-sm font-medium text-slate-700"
						>Description</label
					>
					<input
						id="adjust-desc"
						type="text"
						placeholder="e.g. Service cancellation credit"
						bind:value={adjustDescription}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div class="flex justify-end gap-3 pt-2">
					<Dialog.Close
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={adjustBusy}
						aria-busy={adjustBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if adjustBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Add adjustment
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Edit discount dialog -->
<Dialog.Root bind:open={discountOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Edit discount</Dialog.Title>
				<Dialog.Close
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Single active discount — a new value replaces the current one. It feeds the ledger balance
				and is auto-applied to new invoices.
			</Dialog.Description>

			{#if discountErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{discountErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					saveDiscount();
				}}
			>
				<div>
					<label for="discount-type" class="block text-sm font-medium text-slate-700">Type</label>
					<select
						id="discount-type"
						bind:value={discountType}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						<option value="">None</option>
						<option value="percentage">Percentage</option>
						<option value="fixed">Fixed amount</option>
					</select>
				</div>
				<div>
					<label for="discount-value" class="block text-sm font-medium text-slate-700">Value</label>
					<input
						id="discount-value"
						type="number"
						min="0"
						step={discountType === 'percentage' ? '1' : '0.01'}
						placeholder={discountType === 'percentage' ? '10' : '0.00'}
						disabled={discountType === ''}
						bind:value={discountValue}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
					/>
					{#if discountType === 'percentage'}
						<p class="mt-1 text-xs text-slate-500">Percent of the ledger subtotal.</p>
					{:else if discountType === 'fixed'}
						<p class="mt-1 text-xs text-slate-500">Flat amount off the ledger subtotal.</p>
					{/if}
				</div>
				<div class="flex justify-end gap-3 pt-2">
					<Dialog.Close
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={discountBusy}
						aria-busy={discountBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if discountBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Save discount
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Add service modal -->
<Dialog.Root bind:open={addOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Add service</Dialog.Title>
				<Dialog.Close
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Adding a service creates new milestones and bills via a new invoice (FR-7.6).
			</Dialog.Description>

			{#if addErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{addErr}
				</p>
			{/if}

			{#if servicesLoading}
				<div class="mt-4 flex items-center gap-2 text-sm text-slate-600">
					<Spinner class="h-4 w-4 text-indigo-600" /> Loading services…
				</div>
			{:else if availableToAttach.length === 0}
				<p class="mt-4 text-sm text-slate-500">No more services available to add.</p>
			{:else}
				<ul
					class="mt-4 max-h-72 space-y-2 overflow-y-auto"
					role="group"
					aria-label="Available services"
				>
					{#each availableToAttach as svc (svc.id)}
						{@const checked = addSelected.includes(svc.id)}
						{@const priceErr = checked ? addPriceError(svc.id) : null}
						<li>
							<div
								class="flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
							>
								<input
									id={`add-svc-${svc.id}`}
									type="checkbox"
									{checked}
									onchange={() => toggleAddService(svc)}
									class="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
								<div class="min-w-0 flex-1">
									<label for={`add-svc-${svc.id}`} class="cursor-pointer">
										<span class="block text-sm font-medium text-slate-900">{svc.name}</span>
										<span class="mt-0.5 block text-xs text-slate-500">
											{svc.step_count}
											{svc.step_count === 1 ? 'step' : 'steps'}
											{#if svc.default_price}· default {fmtPrice(svc.default_price)}{/if}
										</span>
										{#if svc.description}
											<span class="mt-1 block text-xs text-slate-600">{svc.description}</span>
										{/if}
									</label>
									{#if checked}
										<div class="mt-2 flex max-w-xs items-center gap-2">
											<label
												for={`add-price-${svc.id}`}
												class="shrink-0 text-xs font-medium text-slate-600">Price</label
											>
											<input
												id={`add-price-${svc.id}`}
												type="number"
												min="0.01"
												step="0.01"
												placeholder="Default price"
												bind:value={addPrices[svc.id]}
												class="w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
											/>
										</div>
										{#if priceErr}
											<p role="alert" class="mt-1 text-xs text-red-600">{priceErr}</p>
										{/if}
									{/if}
								</div>
							</div>
						</li>
					{/each}
				</ul>

				{#if addSelected.length > 0}
					<div class="mt-3">
						<button
							type="button"
							onclick={() => (addPreviewOpen = !addPreviewOpen)}
							aria-expanded={addPreviewOpen}
							aria-controls="add-preview-steps"
							class="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="h-4 w-4 transition-transform {addPreviewOpen ? 'rotate-90' : ''}"
								aria-hidden="true"
							>
								<path
									fill-rule="evenodd"
									d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
									clip-rule="evenodd"
								/>
							</svg>
							{addPreviewOpen ? 'Hide' : 'Preview'} milestones
						</button>
					</div>
					{#if addPreviewOpen}
						<div
							id="add-preview-steps"
							class="mt-2 max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"
						>
							{#each addSelected as sid (sid)}
								{@const detail = allServiceDetails[sid]}
								{@const svc = allServices.find((s) => s.id === sid)}
								{#if detail}
									<div>
										<p class="text-xs font-semibold text-slate-700">{svc?.name ?? 'Service'}</p>
										<ol class="ml-4 list-decimal">
											{#each detail as st (st.id ?? `${st.sequence_order}`)}
												<li>
													{st.name}
													{#if st.expected_duration_days}
														<span class="text-xs text-slate-500"
															>({st.expected_duration_days}d)</span
														>
													{/if}
												</li>
											{/each}
										</ol>
									</div>
								{:else}
									<p class="text-xs text-slate-500">Loading {svc?.name ?? '…'}…</p>
								{/if}
							{/each}
						</div>
					{/if}
				{/if}
			{/if}

			<div class="mt-6 flex justify-end gap-3">
				<Dialog.Close
					class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Cancel
				</Dialog.Close>
				<button
					type="button"
					disabled={addBusy || addSelected.length === 0}
					aria-busy={addBusy}
					onclick={confirmAdd}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if addBusy}<Spinner class="h-4 w-4 text-white" />{/if}
					Add
				</button>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Statement preview modal -->
<Dialog.Root bind:open={statementOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-3xl -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none max-h-[90vh] overflow-y-auto"
		>
			<div class="flex items-center justify-between border-b border-slate-200 pb-3">
				<div>
					<Dialog.Title class="text-lg font-semibold text-slate-900">Project Financial Statement</Dialog.Title>
					<Dialog.Description class="text-xs text-slate-500">Live chronological statement of account for {data.project.name}</Dialog.Description>
				</div>
				<Dialog.Close
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-5 w-5" aria-hidden="true">
						<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
					</svg>
				</Dialog.Close>
			</div>

			{#if statementErr}
				<p role="alert" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
					{statementErr}
				</p>
			{/if}

			{#if statementLoading}
				<div class="flex items-center justify-center py-12">
					<Spinner class="h-8 w-8 text-indigo-600" />
				</div>
			{:else if statementData}
				{@const summary = statementData.summary}
				<div class="mt-4 space-y-4">
					<!-- Summary grid -->
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-md border border-slate-200">
						<div>
							<span class="text-xs text-slate-500">Total Charges</span>
							<p class="font-semibold text-slate-900">{fmtPrice(summary.total)}</p>
						</div>
						<div>
							<span class="text-xs text-slate-500">Total Paid</span>
							<p class="font-semibold text-green-700">{fmtPrice(summary.paid)}</p>
						</div>
						<div>
							<span class="text-xs text-slate-500">Balance Due</span>
							<p class="font-bold {Number(summary.due) > 0 ? 'text-red-600' : 'text-green-700'}">{fmtPrice(summary.due)}</p>
						</div>
						{#if Number(summary.advance_balance) > 0}
							<div>
								<span class="text-xs text-indigo-600 font-medium">Advance Credit</span>
								<p class="font-bold text-indigo-700">{fmtPrice(summary.advance_balance)}</p>
							</div>
						{/if}
					</div>

					<!-- Entries table -->
					<div class="border border-slate-200 rounded-md overflow-hidden">
						<table class="min-w-full divide-y divide-slate-200 text-sm">
							<thead class="bg-slate-50 text-slate-700 font-medium">
								<tr>
									<th scope="col" class="px-3 py-2 text-left">Date</th>
									<th scope="col" class="px-3 py-2 text-left">Type</th>
									<th scope="col" class="px-3 py-2 text-left">Description / Ref</th>
									<th scope="col" class="px-3 py-2 text-right">Amount</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100 bg-white">
								{#if statementData.entries.length === 0}
									<tr>
										<td colspan="4" class="px-3 py-4 text-center text-slate-500">No transactions or services recorded yet.</td>
									</tr>
								{:else}
									{#each statementData.entries as entry (entry.id)}
										{@const meta = entryMeta(entry)}
										<tr>
											<td class="px-3 py-2 text-slate-600 whitespace-nowrap">{entry.entry_date ? formatDate(entry.entry_date) : formatDateTime(entry.created_at)}</td>
											<td class="px-3 py-2 capitalize font-medium {meta.text}">{entry.type}</td>
											<td class="px-3 py-2 text-slate-900">{entryLabel(entry)}</td>
											<td class="px-3 py-2 text-right font-semibold {meta.text}">{entryPrice(entry)}</td>
										</tr>
									{/each}
								{/if}
							</tbody>
						</table>
					</div>

					<!-- Actions -->
					<div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-200">
						<div class="flex gap-2">
							<button
								type="button"
								disabled={statementPdfBusy}
								onclick={viewStatementPdf}
								class="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
							>
								{#if statementPdfBusy}<Spinner class="h-3.5 w-3.5 text-slate-600" />{/if}
								View PDF
							</button>
							<button
								type="button"
								disabled={statementPdfBusy}
								onclick={downloadStatementPdf}
								class="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
							>
								Download PDF
							</button>
						</div>
						<div class="flex gap-2">
							<Dialog.Close class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
								Close
							</Dialog.Close>
							{#if canManage}
								<button
									type="button"
									onclick={openGenerateDialog}
									class="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
								>
									Generate Official Invoice
								</button>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Generate invoice confirmation dialog -->
<Dialog.Root bind:open={generateOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Generate Statement Invoice</Dialog.Title>
				<Dialog.Close
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-5 w-5" aria-hidden="true">
						<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
					</svg>
				</Dialog.Close>
			</div>

			<Dialog.Description class="mt-2 text-sm text-slate-600">
				This will freeze the current project financial state into an official issued invoice with the next sequential invoice number (<code class="text-indigo-600 font-semibold">INV-XXXX</code>).
			</Dialog.Description>

			{#if generateErr}
				<p role="alert" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
					{generateErr}
				</p>
			{/if}

			{#if ledgerSummary}
				<div class="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-md text-sm space-y-1">
					<div class="flex justify-between"><span class="text-slate-500">Project Charges:</span> <span class="font-semibold text-slate-900">{fmtPrice(ledgerSummary.total)}</span></div>
					<div class="flex justify-between"><span class="text-slate-500">Total Payments:</span> <span class="font-semibold text-green-700">{fmtPrice(ledgerSummary.paid)}</span></div>
					<div class="flex justify-between border-t border-slate-200 pt-1"><span class="text-slate-700 font-medium">Net Due:</span> <span class="font-bold text-slate-900">{fmtPrice(ledgerSummary.due)}</span></div>
					{#if Number(ledgerSummary.advance_balance) > 0}
						<div class="flex justify-between text-indigo-700"><span class="font-medium">Advance Credit:</span> <span class="font-bold">{fmtPrice(ledgerSummary.advance_balance)}</span></div>
					{/if}
				</div>
			{/if}

			<div class="mt-6 flex justify-end gap-3">
				<Dialog.Close
					class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Cancel
				</Dialog.Close>
				<button
					type="button"
					disabled={generateBusy}
					aria-busy={generateBusy}
					onclick={runGenerateInvoice}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if generateBusy}<Spinner class="h-4 w-4 text-white" />{/if}
					Confirm & Issue Invoice
				</button>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Record project payment dialog -->
<Dialog.Root bind:open={paymentOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Record Project Payment</Dialog.Title>
				<Dialog.Close
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-5 w-5" aria-hidden="true">
						<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
					</svg>
				</Dialog.Close>
			</div>

			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Record a payment or transaction received directly for this project. It will synchronize across the live ledger and balance-forward statement.
			</Dialog.Description>

			{#if paymentErr}
				<p role="alert" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
					{paymentErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					savePayment();
				}}
			>
				<div>
					<label for="pay-amount" class="block text-sm font-medium text-slate-700">Amount received</label>
					<div class="relative mt-1 rounded-md shadow-sm">
						<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
							<span class="text-slate-500 sm:text-sm">$</span>
						</div>
						<input
							id="pay-amount"
							type="number"
							step="0.01"
							min="0.01"
							placeholder="0.00"
							bind:value={paymentAmount}
							required
							class="block w-full rounded-md border-slate-300 pl-7 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label for="pay-method" class="block text-sm font-medium text-slate-700">Payment method</label>
						<select
							id="pay-method"
							bind:value={paymentMethod}
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						>
							<option value="bank_transfer">Bank Transfer</option>
							<option value="card">Credit Card</option>
							<option value="cash">Cash</option>
							<option value="other">Other</option>
						</select>
					</div>
					<div>
						<label for="pay-date" class="block text-sm font-medium text-slate-700">Payment date</label>
						<input
							id="pay-date"
							type="date"
							bind:value={paymentDate}
							required
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
				</div>

				<div>
					<label for="pay-note" class="block text-sm font-medium text-slate-700">Reference / Note (optional)</label>
					<input
						id="pay-note"
						type="text"
						placeholder="Check #, Wire reference, Deposit memo..."
						bind:value={paymentNote}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="mt-6 flex justify-end gap-3 pt-2">
					<Dialog.Close
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={paymentBusy}
						aria-busy={paymentBusy}
						class="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if paymentBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Save payment
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- File Upload Dialog -->
{#if showFileUploadModal}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs"
		role="dialog"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
			<div class="flex items-center justify-between border-b border-slate-100 pb-3">
				<h2 class="text-lg font-semibold text-slate-900">Upload Project File</h2>
				<button
					type="button"
					onclick={() => (showFileUploadModal = false)}
					class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			{#if uploadErr}
				<p class="mt-3 rounded-md bg-red-50 p-2.5 text-sm text-red-700">{uploadErr}</p>
			{/if}

			<div class="mt-4 space-y-4">
				<!-- File Destination / Service Folder -->
				<div>
					<label for="upload-target-modal" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
						Attach To
					</label>
					<select
						id="upload-target-modal"
						bind:value={uploadTargetChoice}
						class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					>
						<option value="general">📁 General Project Files (Root)</option>
						{#if activeServicesList.length > 0}
							<optgroup label="Attach to Service">
								{#each activeServicesList as s (s.id)}
									<option value={`service:${s.service_id}`}>
										⚡ {data.serviceDetails[s.service_id]?.name ?? 'Service'}
									</option>
								{/each}
							</optgroup>
						{/if}
						{#if projectFolderNodes.length > 0}
							<optgroup label="Project Folders">
								{#each projectFolderNodes as fn (fn.id)}
									<option value={`folder:${fn.id}`}>📁 {fn.name}</option>
								{/each}
							</optgroup>
						{/if}
					</select>
					<p class="mt-1 text-xs text-slate-500">
						Files uploaded here stay in sync with the central Files repository under Project Files.
					</p>
				</div>

				<!-- File Picker -->
				<div>
					<label for="file-upload-input" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
						Select File(s)
					</label>
					<input
						id="file-upload-input"
						type="file"
						multiple
						onchange={handleFileUpload}
						disabled={uploadBusy}
						class="mt-1.5 block w-full text-sm text-slate-500 file:mr-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-xs file:font-semibold file:text-indigo-700 hover:file:bg-indigo-100"
					/>
				</div>

				{#if uploadBusy}
					<div class="flex items-center justify-center gap-2 py-4 text-sm text-indigo-600">
						<Spinner class="h-5 w-5 text-indigo-600" />
						Uploading file(s)...
					</div>
				{/if}
			</div>

			<div class="mt-6 flex justify-end">
				<button
					type="button"
					onclick={() => (showFileUploadModal = false)}
					class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- File Rename Dialog -->
{#if renameTarget}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs"
		role="dialog"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
			<div class="flex items-center justify-between border-b border-slate-100 pb-3">
				<h2 class="text-lg font-semibold text-slate-900">Rename File</h2>
				<button
					type="button"
					onclick={() => (renameTarget = null)}
					class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			{#if renameErr}
				<p class="mt-3 rounded-md bg-red-50 p-2.5 text-sm text-red-700">{renameErr}</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					executeFileRename();
				}}
			>
				<div>
					<label for="new-file-name" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
						File Name
					</label>
					<input
						id="new-file-name"
						type="text"
						bind:value={newFileName}
						required
						class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="mt-6 flex justify-end gap-3">
					<button
						type="button"
						onclick={() => (renameTarget = null)}
						class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={renameBusy}
						class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
					>
						{#if renameBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Save
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- File Preview Modal -->
{#if previewTarget}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4 backdrop-blur-xs"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-2xl">
			<div class="flex items-center justify-between border-b border-slate-200 px-6 py-4">
				<div>
					<h2 class="text-base font-semibold text-slate-900">{previewTarget.name}</h2>
					<p class="text-xs text-slate-500">{fmtBytes(previewTarget.size_bytes)} • {previewTarget.content_type}</p>
				</div>
				<div class="flex items-center gap-2">
					<button
						type="button"
						onclick={() => handleFileDownload(previewTarget)}
						class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
					>
						Download
					</button>
					<button
						type="button"
						onclick={() => (previewTarget = null)}
						class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
					>
						<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>

			<div class="flex flex-1 items-center justify-center overflow-auto p-6 bg-slate-50">
				{#if previewLoading}
					<Spinner class="h-8 w-8 text-indigo-600" />
				{:else if previewUrl && previewTarget.content_type.startsWith('image/')}
					<img src={previewUrl} alt={previewTarget.name} class="max-h-[70vh] rounded-lg object-contain shadow-sm" />
				{:else if previewUrl && previewTarget.content_type === 'application/pdf'}
					<iframe src={previewUrl} title={previewTarget.name} class="h-[70vh] w-full rounded-lg border border-slate-200"></iframe>
				{:else}
					<div class="text-center py-12">
						<p class="text-sm font-medium text-slate-900">Preview not available for this file type</p>
						<p class="mt-1 text-xs text-slate-500">Download the file to view its full content.</p>
						<button
							type="button"
							onclick={() => handleFileDownload(previewTarget)}
							class="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
						>
							Download File
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Delete File Confirm Dialog -->
<ConfirmDialog
	bind:open={
		() => deleteFileTarget !== null,
		(v) => {
			if (!v) deleteFileTarget = null;
		}
	}
	title="Delete File"
	description={deleteFileTarget ? `Permanently delete "${deleteFileTarget.name}" from this project?` : ''}
	confirmLabel="Delete"
	destructive
	busy={deleteFileBusy}
	onconfirm={executeFileDelete}
/>

