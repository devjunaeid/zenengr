/**
 * Shared formatting helpers.
 *
 * Price/date/time helpers are tenant-aware: they read the reactive
 * `tenantSettings` store internally, so every call site follows the
 * tenant's currency/timezone/date_format/time_format without passing
 * settings around. Intl formatters are cached per key (currency, timezone,
 * hour cycle) to avoid re-allocating them on every render.
 */
import { tenantSettings } from '$lib/stores/settings.svelte.js';

/**
 * Allowed date format templates (also used by the configuration page).
 * @type {readonly string[]}
 */
export const DATE_FORMATS = [
	'YYYY-MM-DD',
	'DD-MM-YYYY',
	'MM-DD-YYYY',
	'DD/MM/YYYY',
	'MM/DD/YYYY',
	'YYYY/MM/DD',
	'DD.MM.YYYY',
	'MM.DD.YYYY',
	'DD MMM YYYY',
	'MMM D, YYYY',
	'D MMMM YYYY',
	'MMMM D, YYYY'
];

/** Matches date-only ISO strings like "2026-03-05" (no time component). */
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;

/** @type {Map<string, Intl.NumberFormat>} */
const priceFormatters = new Map();
/** @type {Map<string, Intl.DateTimeFormat>} */
const datePartExtractors = new Map();
/** @type {Intl.DateTimeFormat|null} */
let localDatePartExtractor = null;
/** @type {Map<string, Intl.DateTimeFormat>} */
const timeFormatters = new Map();

/** @type {{ short: string[], long: string[] }|null} */
let monthNamesCache = null;

/**
 * Month-name arrays (en-US), computed once from Intl formatters.
 * @param {'short'|'long'} style
 */
function monthNames(style) {
	if (!monthNamesCache) {
		const short = [];
		const long = [];
		const fmtShort = new Intl.DateTimeFormat('en-US', { month: 'short' });
		const fmtLong = new Intl.DateTimeFormat('en-US', { month: 'long' });
		for (let i = 0; i < 12; i++) {
			const d = new Date(2000, i, 1);
			short.push(fmtShort.format(d));
			long.push(fmtLong.format(d));
		}
		monthNamesCache = { short, long };
	}
	return monthNamesCache[style];
}

/**
 * Cached per-timezone date-part extractor. Falls back to UTC when the
 * configured timezone is not a valid IANA name (never cached on failure).
 * @param {string} timeZone
 */
function getDateParts(timeZone) {
	let fmt = datePartExtractors.get(timeZone);
	if (!fmt) {
		try {
			fmt = new Intl.DateTimeFormat('en-US', {
				timeZone,
				year: 'numeric',
				month: 'numeric',
				day: 'numeric'
			});
			datePartExtractors.set(timeZone, fmt);
		} catch {
			return getDateParts('UTC');
		}
	}
	return fmt;
}

/**
 * Cached date-part extractor with NO timezone option: reads the calendar
 * fields as literally given to the Date object (local naive date). Used for
 * date-only ISO strings so they render as-is in any tenant/browser timezone.
 * @returns {Intl.DateTimeFormat}
 */
function getLocalDateParts() {
	if (!localDatePartExtractor) {
		localDatePartExtractor = new Intl.DateTimeFormat('en-US', {
			year: 'numeric',
			month: 'numeric',
			day: 'numeric'
		});
	}
	return localDatePartExtractor;
}

/**
 * Format a date-only ISO string or datetime into a tenant template.
 * Tokens: YYYY, YY, MMMM, MMM, MM, M, DD, D.
 *
 * @param {string|null|undefined} iso
 * @param {{ date_format?: string, timezone?: string }} [overrides] explicit template/timezone (used by the configuration demo)
 * @returns {string}
 */
export function formatDate(iso, overrides = {}) {
	if (!iso) return '—';
	const dateOnly = typeof iso === 'string' && DATE_ONLY_RE.test(iso);
	const d = dateOnly
		? (() => {
				const [y, m, day] = iso.split('-').map(Number);
				return new Date(y, m - 1, day);
			})()
		: new Date(iso);
	if (Number.isNaN(d.getTime())) return '';
	const settings = tenantSettings;
	const template = overrides.date_format ?? settings.date_format;
	const timeZone = overrides.timezone ?? settings.timezone;

	const fmt = dateOnly ? getLocalDateParts() : getDateParts(timeZone);
	const parts = fmt.formatToParts(d);
	/** @type {Record<string, string>} */
	const byType = {};
	for (const p of parts) byType[p.type] = p.value;

	const year = byType.year ?? '????';
	const monthNum = parseInt(byType.month, 10);
	const dayNum = parseInt(byType.day, 10);
	const months = monthNames('long');
	const monthsShort = monthNames('short');

	// Single-pass token replace: longest tokens first so "MMMM" is not eaten
	// by "MM", and month names inserted as values are never rescanned.
	return template.replace(/YYYY|YY|MMMM|MMM|MM|M|DD|D/g, (tok) => {
		switch (tok) {
			case 'YYYY':
				return year;
			case 'YY':
				return year.slice(-2);
			case 'MMMM':
				return months[monthNum - 1] ?? '';
			case 'MMM':
				return monthsShort[monthNum - 1] ?? '';
			case 'MM':
				return String(monthNum).padStart(2, '0');
			case 'M':
				return String(monthNum);
			case 'DD':
				return String(dayNum).padStart(2, '0');
			case 'D':
				return String(dayNum);
			default:
				return tok;
		}
	});
}

/**
 * Format a datetime as HH:mm (24h) or h:mm a (12h) in the tenant timezone.
 *
 * @param {string|null|undefined} iso
 * @param {{ time_format?: string, timezone?: string }} [overrides]
 * @returns {string}
 */
export function formatTime(iso, overrides = {}) {
	if (!iso) return '—';
	if (typeof iso === 'string' && DATE_ONLY_RE.test(iso)) return '';
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return '';
	const settings = tenantSettings;
	const timeZone = overrides.timezone ?? settings.timezone;
	const hour12 = (overrides.time_format ?? settings.time_format) !== '24h';

	const key = `${timeZone}|${hour12 ? '12' : '24'}`;
	let fmt = timeFormatters.get(key);
	if (!fmt) {
		try {
			fmt = new Intl.DateTimeFormat('en-US', {
				timeZone,
				hour: hour12 ? 'numeric' : '2-digit',
				minute: '2-digit',
				hour12
			});
			timeFormatters.set(key, fmt);
		} catch {
			if (timeZone !== 'UTC') return formatTime(iso, { ...overrides, timezone: 'UTC' });
			return '—';
		}
	}
	return fmt.format(d);
}

/**
 * Format an ISO timestamp as date + time in tenant settings.
 * @param {string|null|undefined} iso
 * @returns {string}
 */
export function formatDateTime(iso) {
	if (typeof iso === 'string' && DATE_ONLY_RE.test(iso)) return formatDate(iso);
	return `${formatDate(iso)} ${formatTime(iso)}`;
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
 * Format a number or decimal-string as currency in the tenant currency.
 * Formatter cached per currency code. Explicit `currency` overrides the
 * tenant setting (e.g. client-realm APIs that return a fixed currency).
 *
 * @param {number|string|null|undefined} v
 * @param {string} [currency] 3-letter ISO code; defaults to tenant currency
 * @returns {string}
 */
export function fmtPrice(v, currency) {
	if (v == null || v === '') return '—';
	const n = Number(v);
	if (Number.isNaN(n)) return String(v);
	const cur = currency ?? tenantSettings.currency;
	let fmt = priceFormatters.get(cur);
	if (!fmt) {
		if (!/^[A-Z]{3}$/.test(cur)) return fmtPrice(v, 'USD');
		fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: cur });
		priceFormatters.set(cur, fmt);
	}
	return fmt.format(n);
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
 * Compact relative timestamp for notification lists: "just now", "5m ago",
 * "3h ago", "2d ago", "3w ago", then falls back to the tenant date format.
 * @param {string|null|undefined} iso
 * @returns {string}
 */
export function timeAgo(iso) {
	if (!iso) return '';
	const then = new Date(iso).getTime();
	if (Number.isNaN(then)) return '';
	const seconds = Math.max(0, Math.round((Date.now() - then) / 1000));
	if (seconds < 60) return 'just now';
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	if (days < 7) return `${days}d ago`;
	const weeks = Math.floor(days / 7);
	if (weeks < 5) return `${weeks}w ago`;
	return formatDate(iso);
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

/**
 * Format a project UUID into a short, unique 6-character alphanumeric code.
 * @param {string|null|undefined} id
 * @returns {string}
 */
export function formatProjectCode(id) {
	if (!id) return '';
	const clean = String(id).replace(/[^a-zA-Z0-9]/g, '').slice(0, 6).toUpperCase();
	return `#${clean}`;
}
