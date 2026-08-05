/**
 * Shared formatting helpers.
 */

/**
 * Format an ISO timestamp as a short, local date-time string.
 * @param {string|null|undefined} iso
 */
export function formatDate(iso) {
	if (!iso) return '—';
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return String(iso);
	return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/**
 * Format an ISO timestamp with time.
 * @param {string|null|undefined} iso
 */
export function formatDateTime(iso) {
	if (!iso) return '—';
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return String(iso);
	return d.toLocaleString(undefined, {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/**
 * Human label for a snake_case status/key: "past_due" -> "Past due".
 * @param {string|null|undefined} value
 */
export function humanize(value) {
	if (!value) return '—';
	const text = String(value).replace(/_/g, ' ');
	return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Format a number or decimal-string as USD currency.
 * @param {number|string|null|undefined} v
 */
export function fmtPrice(v) {
	if (v == null || v === '') return '—';
	const n = Number(v);
	if (Number.isNaN(n)) return '—';
	return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}

/**
 * Format a byte count as a human-readable size, e.g. "1.2 MB".
 * @param {number|string|null|undefined} bytes
 */
export function fmtBytes(bytes) {
	if (bytes == null || bytes === '') return '—';
	const n = Number(bytes);
	if (Number.isNaN(n) || n < 0) return '—';
	if (n < 1024) return `${n} B`;
	const units = ['KB', 'MB', 'GB', 'TB'];
	let value = n;
	let unit = 'B';
	for (const u of units) {
		value /= 1024;
		if (value < 1024) {
			unit = u;
			break;
		}
	}
	return `${value >= 100 ? Math.round(value) : value.toFixed(1)} ${unit}`;
}

/**
 * Slugify a business name: lowercase, alnum + dashes.
 * @param {string} value
 */
export function slugify(value) {
	return value
		.toLowerCase()
		.trim()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}
