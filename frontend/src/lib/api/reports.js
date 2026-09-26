import { apiFetch } from './client.js';

/**
 * Company global ledger and analytics reporting API endpoints (FEAT-025, TODO-213/214).
 */

/**
 * @typedef {object} CompanyLedgerSummary
 * @property {string|null} period_from
 * @property {string|null} period_to
 * @property {number} new_projects_count
 * @property {number} new_clients_count
 * @property {number} new_services_count
 * @property {string} new_services_value
 * @property {string} total_invoiced
 * @property {string} total_collected
 * @property {string} total_due
 * @property {string} total_advance_balance
 */

/**
 * @typedef {object} CompanyLedgerTimelineItem
 * @property {string} period
 * @property {string} period_label
 * @property {number} new_projects
 * @property {number} new_clients
 * @property {number} new_services
 * @property {string} invoiced_amount
 * @property {string} collected_amount
 * @property {string} net_due_change
 */

/**
 * @typedef {object} CompanyLedgerProjectItem
 * @property {string} project_id
 * @property {string} short_id
 * @property {string} name
 * @property {string} client_id
 * @property {string} client_name
 * @property {string} status
 * @property {string} created_at
 * @property {number} services_count
 * @property {string} total_value
 * @property {string} total_invoiced
 * @property {string} total_paid
 * @property {string} balance_due
 */

/**
 * @typedef {object} CompanyLedgerClientItem
 * @property {string} client_id
 * @property {string} name
 * @property {string} client_type
 * @property {string} created_at
 * @property {number} active_projects_count
 * @property {number} total_services_count
 * @property {string} total_invoiced
 * @property {string} total_paid
 * @property {string} total_due
 * @property {string} advance_balance
 */

/**
 * @typedef {object} CompanyLedgerResponse
 * @property {CompanyLedgerSummary} summary
 * @property {CompanyLedgerTimelineItem[]} timeline
 * @property {CompanyLedgerProjectItem[]} projects
 * @property {CompanyLedgerClientItem[]} clients
 * @property {Record<string, any>} filters_applied
 */

/**
 * Fetch company-wide global ledger and operational analytics.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {object} [params]
 * @param {string} [params.date_from]
 * @param {string} [params.date_to]
 * @param {string} [params.client_id]
 * @param {string} [params.project_id]
 * @param {'month'|'day'} [params.granularity]
 * @param {'all'|'timeline'|'projects'|'clients'} [params.tab]
 * @returns {Promise<CompanyLedgerResponse>}
 */
export function getCompanyLedger(fetchFn, token, params = {}) {
	const sp = new URLSearchParams();
	if (params.date_from) sp.set('date_from', params.date_from);
	if (params.date_to) sp.set('date_to', params.date_to);
	if (params.client_id) sp.set('client_id', params.client_id);
	if (params.project_id) sp.set('project_id', params.project_id);
	if (params.granularity) sp.set('granularity', params.granularity);
	if (params.tab) sp.set('tab', params.tab);

	const qs = sp.toString();
	const path = qs ? `/tenant/reports/company-ledger?${qs}` : '/tenant/reports/company-ledger';
	return apiFetch(fetchFn, path, { token });
}
