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
