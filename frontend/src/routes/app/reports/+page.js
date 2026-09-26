import * as reportsApi from '$lib/api/reports.js';
import { auth } from '$lib/stores/auth.svelte.js';

/**
 * Compute start and end dates for quick presets.
 *
 * @param {string} preset
 * @returns {{ date_from: string | null, date_to: string | null }}
 */
function resolvePresetDates(preset) {
	const now = new Date();
	const y = now.getFullYear();
	const m = now.getMonth(); // 0-indexed

	/** @param {Date} d */
	const iso = (d) => {
		const year = d.getFullYear();
		const month = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		return `${year}-${month}-${day}`;
	};

	switch (preset) {
		case 'this_month': {
			const start = new Date(y, m, 1);
			const end = new Date(y, m + 1, 0);
			return { date_from: iso(start), date_to: iso(end) };
		}
		case 'last_month': {
			const start = new Date(y, m - 1, 1);
			const end = new Date(y, m, 0);
			return { date_from: iso(start), date_to: iso(end) };
		}
		case 'this_quarter': {
			const qStartMonth = Math.floor(m / 3) * 3;
			const start = new Date(y, qStartMonth, 1);
			const end = new Date(y, qStartMonth + 3, 0);
			return { date_from: iso(start), date_to: iso(end) };
		}
		case 'ytd': {
			const start = new Date(y, 0, 1);
			return { date_from: iso(start), date_to: iso(now) };
		}
		case 'last_30_days': {
			const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
			return { date_from: iso(start), date_to: iso(now) };
		}
		case 'last_90_days': {
			const start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
			return { date_from: iso(start), date_to: iso(now) };
		}
		case 'all_time': {
			return { date_from: null, date_to: null };
		}
		default:
			return { date_from: null, date_to: null };
	}
}

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const preset = url.searchParams.get('preset') || 'this_month';
	let dateFrom = url.searchParams.get('date_from');
	let dateTo = url.searchParams.get('date_to');

	if (preset !== 'custom' && (!dateFrom || !dateTo)) {
		const resolved = resolvePresetDates(preset);
		dateFrom = resolved.date_from;
		dateTo = resolved.date_to;
	}

	const clientId = url.searchParams.get('client_id') || '';
	const projectId = url.searchParams.get('project_id') || '';
	const granularity = url.searchParams.get('granularity') === 'day' ? 'day' : 'month';
	const tab = url.searchParams.get('tab') || 'timeline';

	/** @type {import('$lib/api/reports.js').CompanyLedgerResponse} */
	let ledgerData = {
		summary: {
			period_from: dateFrom,
			period_to: dateTo,
			new_projects_count: 0,
			new_clients_count: 0,
			new_services_count: 0,
			new_services_value: '0.00',
			total_invoiced: '0.00',
			total_collected: '0.00',
			total_due: '0.00',
			total_advance_balance: '0.00'
		},
		timeline: [],
		projects: [],
		clients: [],
		filters_applied: {}
	};
	let loadError = null;

	try {
		ledgerData = await reportsApi.getCompanyLedger(fetch, token, {
			...(dateFrom && { date_from: dateFrom }),
			...(dateTo && { date_to: dateTo }),
			...(clientId && { client_id: clientId }),
			...(projectId && { project_id: projectId }),
			granularity,
			tab: 'all' // Backend warm execution now takes ~300ms for all tabs, or tab can be used
		});
	} catch (err) {
		console.error('Failed to load company ledger:', err);
		loadError = 'Unable to load company reports. Please refresh to try again.';
	}

	return {
		ledgerData,
		loadError,
		filters: {
			preset,
			date_from: dateFrom,
			date_to: dateTo,
			client_id: clientId,
			project_id: projectId,
			granularity,
			tab
		}
	};
}
