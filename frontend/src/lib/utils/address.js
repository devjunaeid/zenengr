/**
 * Billing address helpers.
 *
 * The backend stores `billing_address` as an opaque JSONB dict. All keys are
 * optional strings; empty values are omitted from the stored dict. These
 * helpers are tolerant of legacy/missing shapes (older records used
 * `line1`/`line2`/`postal` keys, or a JSON string).
 */

/**
 * @typedef {object} AddressFields
 * @property {string} address_line1
 * @property {string} address_line2
 * @property {string} city
 * @property {string} state
 * @property {string} postal_code
 * @property {string} country
 */

/**
 * Keys stored in the billing_address dict, in display order.
 * @type {readonly ['address_line1','address_line2','city','state','postal_code','country']}
 */
export const ADDRESS_KEYS = [
	'address_line1',
	'address_line2',
	'city',
	'state',
	'postal_code',
	'country'
];

/**
 * Legacy key names used by older records, per current key.
 * @type {Partial<Record<keyof AddressFields, string>>}
 */
const LEGACY_KEYS = { address_line1: 'line1', address_line2: 'line2', postal_code: 'postal' };

/**
 * Normalize a stored billing_address dict into editable field values.
 * Tolerant of null/missing/legacy shapes; unknown input yields empty fields.
 *
 * @param {Record<string, any>|string|null|undefined} obj
 * @returns {AddressFields}
 */
export function addressToFields(obj) {
	/** @type {AddressFields} */
	const fields = {
		address_line1: '',
		address_line2: '',
		city: '',
		state: '',
		postal_code: '',
		country: ''
	};
	if (!obj || typeof obj !== 'object') return fields;
	for (const key of ADDRESS_KEYS) {
		const legacy = LEGACY_KEYS[key];
		const raw = obj[key] ?? (legacy ? obj[legacy] : undefined);
		fields[key] = typeof raw === 'string' ? raw : '';
	}
	return fields;
}

/**
 * Build a billing_address dict from form fields, omitting empty values.
 * Returns `{}` when every field is empty.
 *
 * @param {Partial<AddressFields>|Record<string, any>} fields
 * @returns {Record<string, string>}
 */
export function fieldsToAddress(fields) {
	/** @type {Record<string, string>} */
	const addr = {};
	for (const key of ADDRESS_KEYS) {
		const val = fields[key];
		if (typeof val === 'string' && val.trim()) addr[key] = val.trim();
	}
	return addr;
}

/**
 * Render a billing_address as a display string:
 * "line1\nline2\ncity, state postal_code\ncountry", skipping empties.
 * Returns '' when nothing is present. Non-object input (e.g. a JSON string)
 * is parsed first, then falls back to the raw string.
 *
 * @param {Record<string, any>|string|null|undefined} obj
 * @returns {string}
 */
export function formatAddress(obj) {
	if (!obj) return '';
	if (typeof obj === 'string') {
		try {
			const parsed = /** @type {unknown} */ (JSON.parse(obj));
			if (parsed && typeof parsed === 'object') return formatAddress(parsed);
		} catch {
			// not JSON — fall through and show the raw string
		}
		return obj;
	}
	if (typeof obj !== 'object') return '';
	const fields = addressToFields(obj);
	const lines = [];
	if (fields.address_line1) lines.push(fields.address_line1);
	if (fields.address_line2) lines.push(fields.address_line2);
	const cityLine = [fields.city, fields.state, fields.postal_code].filter(Boolean).join(', ');
	if (cityLine) lines.push(cityLine);
	if (fields.country) lines.push(fields.country);
	return lines.join('\n');
}
