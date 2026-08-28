/**
 * Tenant-wide display settings (currency, timezone, date/time format).
 * Populated by the /app and /client layouts from the backend; consumed
 * reactively by the shared formatting helpers in $lib/utils/format.js.
 *
 * @typedef {object} TenantSettings
 * @property {string} currency 3-letter ISO currency code
 * @property {string} timezone IANA timezone name
 * @property {string} date_format date template from DATE_FORMATS
 * @property {string} time_format '24h' or '12h'
 * @property {boolean} loaded true once backend settings have been applied
 */

/** @type {TenantSettings} */
let state = $state({
	currency: 'USD',
	timezone: 'UTC',
	date_format: 'YYYY-MM-DD',
	time_format: '24h',
	invoice_prefix: 'INV',
	invoice_number_format: '{PREFIX}-{YYYY}-{SEQ:04d}',
	loaded: false
});

/**
 * Reactive tenant settings. Helpers read these getters internally, so
 * components that call them re-render automatically when settings change.
 */
export const tenantSettings = {
	get currency() {
		return state.currency;
	},
	get timezone() {
		return state.timezone;
	},
	get date_format() {
		return state.date_format;
	},
	get time_format() {
		return state.time_format;
	},
	get invoice_prefix() {
		return state.invoice_prefix;
	},
	get invoice_number_format() {
		return state.invoice_number_format;
	},
	get loaded() {
		return state.loaded;
	}
};

/**
 * Merge backend settings into the store. Missing keys keep their current
 * value; marks the store as loaded so callers know defaults were replaced.
 * @param {Partial<Pick<TenantSettings, 'currency'|'timezone'|'date_format'|'time_format'|'invoice_prefix'|'invoice_number_format'>>} s
 */
export function setTenantSettings(s) {
	if (typeof s.currency === 'string' && s.currency) state.currency = s.currency;
	if (typeof s.timezone === 'string' && s.timezone) state.timezone = s.timezone;
	if (typeof s.date_format === 'string' && s.date_format) state.date_format = s.date_format;
	if (typeof s.time_format === 'string' && s.time_format) state.time_format = s.time_format;
	if (typeof s.invoice_prefix === 'string' && s.invoice_prefix) state.invoice_prefix = s.invoice_prefix;
	if (typeof s.invoice_number_format === 'string' && s.invoice_number_format)
		state.invoice_number_format = s.invoice_number_format;
	state.loaded = true;
}
