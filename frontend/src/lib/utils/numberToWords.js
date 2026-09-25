/**
 * Converts numbers into English words supporting both:
 * 1. International system (thousands, millions, billions, trillions)
 * 2. South Asian / Indian system (thousands, lakhs, crores / korti)
 */
import { tenantSettings } from '$lib/stores/settings.svelte.js';

const ONES = [
	'',
	'one',
	'two',
	'three',
	'four',
	'five',
	'six',
	'seven',
	'eight',
	'nine',
	'ten',
	'eleven',
	'twelve',
	'thirteen',
	'fourteen',
	'fifteen',
	'sixteen',
	'seventeen',
	'eighteen',
	'nineteen'
];

const TENS = [
	'',
	'',
	'twenty',
	'thirty',
	'forty',
	'fifty',
	'sixty',
	'seventy',
	'eighty',
	'ninety'
];

/**
 * Converts an integer strictly less than 1,000 into words.
 * @param {number} n
 * @returns {string}
 */
function chunkUnder1000(n) {
	if (n === 0) return '';
	const words = [];
	const hundreds = Math.floor(n / 100);
	const rem = n % 100;

	if (hundreds > 0) {
		words.push(`${ONES[hundreds]} hundred`);
	}

	if (rem > 0) {
		if (rem < 20) {
			words.push(ONES[rem]);
		} else {
			const ten = Math.floor(rem / 10);
			const unit = rem % 10;
			words.push(unit > 0 ? `${TENS[ten]}-${ONES[unit]}` : TENS[ten]);
		}
	}

	return words.join(' ');
}

/**
 * International numbering system conversion (Millions, Billions, Trillions).
 * @param {number} n
 * @returns {string}
 */
function convertInternational(n) {
	if (n === 0) return 'zero';

	const scales = [
		{ value: 1_000_000_000_000, label: 'trillion' },
		{ value: 1_000_000_000, label: 'billion' },
		{ value: 1_000_000, label: 'million' },
		{ value: 1_000, label: 'thousand' }
	];

	const words = [];
	let rem = n;

	for (const scale of scales) {
		if (rem >= scale.value) {
			const count = Math.floor(rem / scale.value);
			words.push(`${convertInternational(count)} ${scale.label}`);
			rem = rem % scale.value;
		}
	}

	if (rem > 0) {
		words.push(chunkUnder1000(rem));
	}

	return words.filter(Boolean).join(' ');
}

/**
 * South Asian numbering system conversion (Thousands, Lakhs, Crores / Korti).
 * - 1,000 = Thousand
 * - 1,00,000 = 1 Lakh
 * - 1,00,00,000 = 1 Crore / Korti
 * @param {number} n
 * @returns {string}
 */
function convertSouthAsian(n) {
	if (n === 0) return 'zero';

	const words = [];
	let rem = n;

	// Crore / Korti (10^7 = 10,000,000)
	if (rem >= 10_000_000) {
		const crores = Math.floor(rem / 10_000_000);
		words.push(`${convertSouthAsian(crores)} crore`);
		rem = rem % 10_000_000;
	}

	// Lakh (10^5 = 100,000)
	if (rem >= 100_000) {
		const lakhs = Math.floor(rem / 100_000);
		words.push(`${chunkUnder1000(lakhs)} lakh`);
		rem = rem % 100_000;
	}

	// Thousand (10^3 = 1,000)
	if (rem >= 1_000) {
		const thousands = Math.floor(rem / 1_000);
		words.push(`${chunkUnder1000(thousands)} thousand`);
		rem = rem % 1_000;
	}

	// Hundreds and remainder
	if (rem > 0) {
		words.push(chunkUnder1000(rem));
	}

	return words.filter(Boolean).join(' ');
}

/**
 * Formats a given number or string into words according to the numbering system.
 *
 * @param {number|string|null|undefined} value
 * @param {'international'|'south_asian'|'indian'} [system] Defaults to tenant setting
 * @param {object} [options]
 * @param {boolean} [options.allowZero=false] If true, returns 'Zero' when value is 0. If false, returns ''
 * @param {boolean} [options.includeDecimals=true] Whether to include fractional cents/paisa as "/100"
 * @returns {string} Words representation or empty string
 */
export function numberToWords(value, system, options = {}) {
	if (value === null || value === undefined || value === '') return '';

	// Clean commas and whitespace
	const cleanStr = String(value).replace(/,/g, '').trim();
	if (!cleanStr) return '';

	const num = Number(cleanStr);
	if (isNaN(num) || !isFinite(num)) return '';

	const allowZero = options.allowZero ?? false;
	const includeDecimals = options.includeDecimals ?? true;

	if (num === 0) {
		return allowZero ? 'Zero' : '';
	}

	const isNegative = num < 0;
	const absNum = Math.abs(num);

	const intPart = Math.floor(absNum);
	const fracPart = Math.round((absNum - intPart) * 100);

	const activeSystem = system || tenantSettings.number_system || 'international';
	const isSouthAsian = activeSystem === 'south_asian' || activeSystem === 'indian';

	let intWords = '';
	if (intPart === 0) {
		intWords = 'zero';
	} else if (isSouthAsian) {
		intWords = convertSouthAsian(intPart);
	} else {
		intWords = convertInternational(intPart);
	}

	let result = intWords;
	if (includeDecimals && fracPart > 0) {
		if (intPart === 0) {
			result = `${fracPart}/100`;
		} else {
			result = `${result} and ${fracPart}/100`;
		}
	}

	if (isNegative) {
		result = `minus ${result}`;
	}

	// Capitalize first character
	result = result.charAt(0).toUpperCase() + result.slice(1);
	return result;
}
