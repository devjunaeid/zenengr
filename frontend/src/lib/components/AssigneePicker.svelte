<script>
	/**
	 * User picker for milestone assignees.
	 *
	 * @type {{
	 *   value: string|null,
	 *   users: Array<{ id: string, full_name: string, email: string }>,
	 *   onchange: (userId: string|null) => Promise<void> | void,
	 *   busy?: boolean,
	 *   disabled?: boolean,
	 *   id?: string
	 * }}
	 */
	let { value, users, onchange, busy = false, disabled = false, id = 'assignee-picker' } = $props();

	let isDisabled = $derived(Boolean(busy) || Boolean(disabled));
	let hasUsers = $derived(users.length > 0);

	/**
	 * @param {Event & { currentTarget: HTMLSelectElement }} e
	 */
	async function handleChange(e) {
		const v = e.currentTarget.value;
		await onchange(v === '' ? null : v);
	}
</script>

<label for={id} class="sr-only">Assignee</label>
<select
	{id}
	value={value ?? ''}
	disabled={isDisabled || !hasUsers}
	aria-busy={busy}
	onchange={handleChange}
	class="block w-full min-w-40 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:opacity-60"
>
	<option value="">— Unassigned —</option>
	{#if hasUsers}
		{#each users as u (u.id)}
			<option value={u.id}>{u.full_name} ({u.email})</option>
		{/each}
	{:else}
		<option value="" disabled>No active users</option>
	{/if}
</select>
