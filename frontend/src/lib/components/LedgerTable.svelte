<script>
	import { formatDateTime, fmtPrice } from '$lib/utils/format.js';

	/**
	 * Read-only ledger table: date, kind badge, signed amount, reference,
	 * running balance. Shared by the staff client detail and client portal.
	 *
	 * @type {{
	 *   entries: Array<{
	 *     id: string,
	 *     kind: 'payment'|'refund'|'advance_received'|'advance_applied',
	 *     amount: string,
	 *     reference: string,
	 *     created_at: string,
	 *     running_balance: string
	 *   }>,
	 *   emptyMessage?: string
	 * }}
	 */
	let { entries, emptyMessage = 'No ledger entries yet.' } = $props();

	/**
	 * Badge classes per entry kind.
	 * @param {'payment'|'refund'|'advance_received'|'advance_applied'} kind
	 */
	function kindBadge(kind) {
		switch (kind) {
			case 'payment':
				return 'bg-green-100 text-green-800 ring-green-600/20';
			case 'refund':
				return 'bg-red-100 text-red-800 ring-red-600/20';
			case 'advance_received':
				return 'bg-amber-100 text-amber-800 ring-amber-600/20';
			case 'advance_applied':
				return 'bg-blue-100 text-blue-800 ring-blue-600/20';
			default:
				return 'bg-slate-100 text-slate-700 ring-slate-500/20';
		}
	}

	/**
	 * Human label per entry kind.
	 * @param {'payment'|'refund'|'advance_received'|'advance_applied'} kind
	 */
	function kindLabel(kind) {
		switch (kind) {
			case 'payment':
				return 'Payment';
			case 'refund':
				return 'Refund';
			case 'advance_received':
				return 'Advance received';
			case 'advance_applied':
				return 'Advance applied';
			default:
				return kind;
		}
	}

	/**
	 * Signed price: "+$1,234.00" / "−$56.00" from a signed decimal string.
	 * @param {string} amount
	 */
	function signedPrice(amount) {
		const n = Number(amount) || 0;
		const abs = fmtPrice(Math.abs(n));
		if (abs === '—') return '—';
		return n < 0 ? `−${abs}` : `+${abs}`;
	}
</script>

{#if entries.length === 0}
	<p class="px-6 py-8 text-sm text-slate-500">{emptyMessage}</p>
{:else}
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-200">
			<thead class="bg-slate-50">
				<tr>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Date</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Kind</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Amount</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Reference</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Running balance</th
					>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-200">
				{#each entries as e (e.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-700"
							>{formatDateTime(e.created_at)}</td
						>
						<td class="px-4 py-3">
							<span
								class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {kindBadge(
									e.kind
								)}"
							>
								{kindLabel(e.kind)}
							</span>
						</td>
						<td class="px-4 py-3 text-right text-sm font-medium whitespace-nowrap text-slate-900"
							>{signedPrice(e.amount)}</td
						>
						<td class="px-4 py-3 text-sm text-slate-700">{e.reference || '—'}</td>
						<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
							>{fmtPrice(e.running_balance)}</td
						>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
