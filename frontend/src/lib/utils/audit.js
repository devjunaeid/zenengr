/**
 * Audit-log helpers shared by the staff audit log, the admin console audit
 * sections and the client-detail activity feed.
 *
 * Backend entries may arrive unenriched (no `actor_name` / `entity_label`)
 * until enrichment lands; every render path falls back to raw fields.
 */
import accountGroup from '@iconify-icons/mdi/account-group';
import accountMultiple from '@iconify-icons/mdi/account-multiple';
import chartBox from '@iconify-icons/mdi/chart-box';
import cog from '@iconify-icons/mdi/cog';
import comment from '@iconify-icons/mdi/comment';
import email from '@iconify-icons/mdi/email';
import emailEdit from '@iconify-icons/mdi/email-edit';
import file from '@iconify-icons/mdi/file';
import folderOpen from '@iconify-icons/mdi/folder-open';
import officeBuilding from '@iconify-icons/mdi/office-building';
import receiptText from '@iconify-icons/mdi/receipt-text';
import shieldAccount from '@iconify-icons/mdi/shield-account';
import tools from '@iconify-icons/mdi/tools';
import cash from '@iconify-icons/mdi/cash';
import { fmtBytes, humanize } from '$lib/utils/format.js';

/**
 * Every audit action the backend can emit, with a human label and a group
 * used for icons, filter optgroups and visual grouping.
 *
 * @type {Record<string, { label: string, group: string }>}
 */
export const AUDIT_ACTIONS = {
	// Tenant
	'tenant.created': { label: 'Tenant created', group: 'Tenant' },
	'tenant.updated': { label: 'Tenant updated', group: 'Tenant' },
	'tenant.profile_updated': { label: 'Profile updated', group: 'Tenant' },
	'tenant.branding.updated': { label: 'Branding updated', group: 'Tenant' },
	'tenant.setting_updated': { label: 'Setting updated', group: 'Tenant' },
	'tenant.flag_set': { label: 'Flag set', group: 'Tenant' },
	'tenant.flag_override_removed': { label: 'Flag override removed', group: 'Tenant' },
	'tenant.suspended': { label: 'Tenant suspended', group: 'Tenant' },
	'tenant.suspend': { label: 'Tenant suspended', group: 'Tenant' },
	'tenant.reactivated': { label: 'Tenant reactivated', group: 'Tenant' },
	'tenant.cancelled': { label: 'Tenant cancelled', group: 'Tenant' },
	'subscription.updated': { label: 'Subscription updated', group: 'Tenant' },

	// Plan
	'plan.created': { label: 'Plan created', group: 'Plan' },
	'plan.updated': { label: 'Plan updated', group: 'Plan' },
	'plan.deleted': { label: 'Plan deleted', group: 'Plan' },
	'plan.flag_default_set': { label: 'Plan flag default set', group: 'Plan' },

	// Client
	'client.created': { label: 'Client created', group: 'Client' },
	'client.updated': { label: 'Client updated', group: 'Client' },
	'client.archived': { label: 'Client archived', group: 'Client' },
	'client.unarchived': { label: 'Client restored', group: 'Client' },
	'client.note_added': { label: 'Note added', group: 'Client' },
	'client.contact_self_updated': { label: 'Contact details updated', group: 'Client' },
	'client_user.invited': { label: 'Client user invited', group: 'Client' },
	'client_user.invite_resent': { label: 'Invite resent', group: 'Client' },
	'client_user.invite_revoked': { label: 'Invite revoked', group: 'Client' },
	'client_user.registered': { label: 'Client user registered', group: 'Client' },
	'client_user.deactivated': { label: 'Client user deactivated', group: 'Client' },
	'client_user.reactivated': { label: 'Client user reactivated', group: 'Client' },

	// Project
	'project.created': { label: 'Project created', group: 'Project' },
	'project.updated': { label: 'Project updated', group: 'Project' },
	'project.service_attached': { label: 'Service attached', group: 'Project' },
	'project.service_cancelled': { label: 'Service cancelled', group: 'Project' },
	'project.service_removed': { label: 'Service removed', group: 'Project' },
	'project.milestone_updated': { label: 'Milestone updated', group: 'Project' },

	// Invoices
	'invoice.created': { label: 'Invoice created', group: 'Invoices' },
	'invoice.updated': { label: 'Invoice updated', group: 'Invoices' },
	'invoice.deleted': { label: 'Invoice deleted', group: 'Invoices' },
	'invoice.issued': { label: 'Invoice issued', group: 'Invoices' },
	'invoice.voided': { label: 'Invoice voided', group: 'Invoices' },

	// Payments
	'invoice.payment_recorded': { label: 'Payment recorded', group: 'Payments' },
	'invoice.refunded': { label: 'Refund recorded', group: 'Payments' },
	'invoice.advance_received': { label: 'Advance received', group: 'Payments' },
	'invoice.advance_applied': { label: 'Advance applied', group: 'Payments' },

	// Service catalog
	'service.created': { label: 'Service created', group: 'Service' },
	'service.updated': { label: 'Service updated', group: 'Service' },
	'service.deleted': { label: 'Service deleted', group: 'Service' },

	// Comment
	'comment.created': { label: 'Comment posted', group: 'Comment' },
	'comment.updated': { label: 'Comment updated', group: 'Comment' },
	'comment.deleted': { label: 'Comment deleted', group: 'Comment' },

	// File
	'file.uploaded': { label: 'File uploaded', group: 'File' },
	'file.downloaded': { label: 'File downloaded', group: 'File' },
	'file.deleted': { label: 'File deleted', group: 'File' },
	'file.renamed': { label: 'File renamed', group: 'File' },
	'file.moved': { label: 'File moved', group: 'File' },
	'file.folder_created': { label: 'Folder created', group: 'File' },
	'file.folder_deleted': { label: 'Folder deleted', group: 'File' },
	'file.folder_renamed': { label: 'Folder renamed', group: 'File' },

	// Roles
	'role.created': { label: 'Role created', group: 'Roles' },
	'role.updated': { label: 'Role updated', group: 'Roles' },
	'role.deleted': { label: 'Role deleted', group: 'Roles' },

	// Users
	'user.registered': { label: 'User registered', group: 'Users' },
	'user.deactivated': { label: 'User deactivated', group: 'Users' },
	'user.reactivated': { label: 'User reactivated', group: 'Users' },
	'user.role_changed': { label: 'Role changed', group: 'Users' },
	'user.password_changed': { label: 'Password changed', group: 'Users' },
	'user.password_reset_initiated': { label: 'Password reset initiated', group: 'Users' },
	'user.password_reset_completed': { label: 'Password reset completed', group: 'Users' },
	'user.email_changed': { label: 'Email changed', group: 'Users' },
	'user.profile_updated': { label: 'Profile updated', group: 'Users' },

	// Invites
	'invite.created': { label: 'Invite created', group: 'Invites' },
	'invite.resent': { label: 'Invite resent', group: 'Invites' },
	'invite.revoked': { label: 'Invite revoked', group: 'Invites' },

	// SMTP
	'smtp_config.updated': { label: 'SMTP config updated', group: 'SMTP' },
	'smtp_config.test': { label: 'SMTP test', group: 'SMTP' },

	// System
	'email.send_failed': { label: 'Email delivery failed', group: 'System' }
};

/**
 * Ordered [{ group, items: [{ value, label }] }] built from AUDIT_ACTIONS,
 * used for grouped <select> filters.
 * @type {Array<{ group: string, items: Array<{ value: string, label: string }> }>}
 */
export const AUDIT_ACTION_OPTIONS = (() => {
	/** @type {Array<{ group: string, items: Array<{ value: string, label: string }> }>} */
	const out = [];
	/** @type {Map<string, Array<{ value: string, label: string }>>} */
	const byGroup = new Map();
	for (const [action, meta] of Object.entries(AUDIT_ACTIONS)) {
		let items = byGroup.get(meta.group);
		if (!items) {
			items = [];
			byGroup.set(meta.group, items);
		}
		items.push({ value: action, label: meta.label });
	}
	for (const [group, items] of byGroup) out.push({ group, items });
	return out;
})();

/**
 * Curated tenant-scoped actions available in tenant app workspace.
 * Omits platform/super-admin only actions (Plan, Tenant suspended/flag overrides).
 */
export const TENANT_AUDIT_ACTION_OPTIONS = (() => {
	const tenantGroups = [
		{
			group: 'Projects & Milestones',
			prefix: 'project.'
		},
		{
			group: 'Invoices',
			prefix: 'invoice.'
		},
		{
			group: 'Clients & CRM',
			prefix: 'client'
		},
		{
			group: 'Team & Staff',
			prefixes: ['user.', 'invite.']
		},
		{
			group: 'Files & Folders',
			prefix: 'file.'
		},
		{
			group: 'Service Catalog',
			prefix: 'service.'
		},
		{
			group: 'Tenant Settings & Branding',
			prefixes: ['tenant.profile_updated', 'tenant.branding.', 'tenant.setting_updated']
		},
		{
			group: 'Email (SMTP)',
			prefix: 'smtp_config.'
		},
		{
			group: 'Roles & Permissions',
			prefix: 'role.'
		},
		{
			group: 'Discussions & Comments',
			prefix: 'comment.'
		}
	];

	/** @type {Array<{ group: string, items: Array<{ value: string, label: string }> }>} */
	const out = [];
	for (const tg of tenantGroups) {
		const items = [];
		for (const [action, meta] of Object.entries(AUDIT_ACTIONS)) {
			let matches = false;
			if (tg.prefix && action.startsWith(tg.prefix)) {
				// Avoid including payment-specific ones in pure invoice group if we want them distinct
				if (tg.prefix === 'invoice.' && (action.includes('payment') || action.includes('refund') || action.includes('advance'))) {
					matches = false;
				} else {
					matches = true;
				}
			} else if (tg.prefixes && tg.prefixes.some((p) => action.startsWith(p))) {
				matches = true;
			}
			if (matches) {
				items.push({ value: action, label: meta.label });
			}
		}
		if (items.length > 0) {
			out.push({ group: tg.group, items });
		}
	}

	// Add Payments group explicitly
	const paymentItems = [];
	for (const [action, meta] of Object.entries(AUDIT_ACTIONS)) {
		if (meta.group === 'Payments') {
			paymentItems.push({ value: action, label: meta.label });
		}
	}
	if (paymentItems.length > 0) {
		out.splice(2, 0, { group: 'Payments & Credits', items: paymentItems });
	}

	return out;
})();

/** @type {Record<string, any>} */
const GROUP_ICONS = {
	Tenant: officeBuilding,
	Plan: chartBox,
	Client: accountGroup,
	Project: folderOpen,
	Invoices: receiptText,
	Payments: cash,
	Service: tools,
	Comment: comment,
	File: file,
	Roles: shieldAccount,
	Users: accountMultiple,
	Invites: emailEdit,
	SMTP: email,
	System: cog
};

/**
 * Human label for an audit action, e.g. "invoice.payment_recorded" ->
 * "Payment recorded". Unknown actions fall back to a humanized action name.
 * @param {string|null|undefined} action
 * @returns {string}
 */
export function auditActionLabel(action) {
	if (!action) return '—';
	const meta = AUDIT_ACTIONS[action];
	if (meta) return meta.label;
	return humanize(String(action).replace(/\./g, ' '));
}

/**
 * Group (resource) an action belongs to. Unknown actions -> "System".
 * @param {string|null|undefined} action
 * @returns {string}
 */
export function auditGroup(action) {
	if (!action) return 'System';
	return AUDIT_ACTIONS[action]?.group ?? 'System';
}

/**
 * mdi icon object for a group; unknown groups get a generic cog.
 * @param {string|null|undefined} group
 * @returns {any}
 */
export function groupIcon(group) {
	return GROUP_ICONS[group ?? ''] ?? cog;
}

/** Known detail keys -> human labels. @type {Record<string, string>} */
const DETAIL_LABELS = {
	changed_keys: 'Changed fields',
	updated_fields: 'Updated fields',
	old_value: 'Value',
	new_value: 'Value',
	project_id: 'Project',
	invoice_id: 'Invoice',
	client_id: 'Client',
	service_id: 'Service',
	invite_id: 'Invite',
	folder_id: 'Folder',
	file_id: 'File',
	parent_id: 'Parent folder',
	project_service_id: 'Project service',
	advance_id: 'Advance',
	amount: 'Amount',
	method: 'Method',
	direction: 'Direction',
	scope: 'Scope',
	size_bytes: 'Size',
	step_count: 'Steps',
	is_internal: 'Internal',
	host: 'Host',
	error: 'Error',
	to_email: 'Recipient',
	invoice_number: 'Invoice number',
	invited_by: 'Invited by'
};

/**
 * Truncate long string values for display.
 * @param {string} s
 * @param {number} [max]
 */
function truncate(s, max = 80) {
	return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

/**
 * Format a single detail value: arrays become comma lists, objects JSON.
 * @param {any} v
 * @returns {string}
 */
function fmtValue(v) {
	if (v == null || v === '') return '—';
	if (Array.isArray(v))
		return v.map((x) => (typeof x === 'string' ? humanize(x) : String(x))).join(', ');
	if (typeof v === 'object') return truncate(JSON.stringify(v));
	if (typeof v === 'boolean') return v ? 'Yes' : 'No';
	return truncate(String(v));
}

/**
 * Label for a detail key, falling back to humanized key name.
 * @param {string} key
 */
function detailLabel(key) {
	return DETAIL_LABELS[key] ?? humanize(key);
}

/**
 * Turn an audit `details` object into [{ label, value }] rows. Paired
 * old_/new_ keys (old_email/new_email, old_name/new_name, old_value/new_value)
 * merge into a single "old -> new" row.
 *
 * @param {Record<string, any>|null|undefined} details
 * @returns {Array<{ label: string, value: string }>}
 */
export function formatAuditDetails(details) {
	if (!details || typeof details !== 'object') return [];
	/** @type {Array<{ label: string, value: string }>} */
	const rows = [];
	/** @type {Set<string>} */
	const consumed = new Set();
	for (const [key, val] of Object.entries(details)) {
		if (consumed.has(key)) continue;
		const pair = /^old_(.+)$/.exec(key);
		if (pair) {
			const base = pair[1];
			const newKey = `new_${base}`;
			if (Object.prototype.hasOwnProperty.call(details, newKey)) {
				rows.push({
					label: detailLabel(newKey),
					value: `${fmtValue(val)} → ${fmtValue(details[newKey])}`
				});
				consumed.add(key);
				consumed.add(newKey);
				continue;
			}
		}
		if (val == null || val === '') continue;
		let value;
		if (key === 'size_bytes') value = fmtBytes(val);
		else value = fmtValue(val);
		rows.push({ label: detailLabel(key), value });
	}
	return rows;
}

/**
 * Tolerant variant used for client-detail activity entries; same shape
 * handling as formatAuditDetails.
 * @param {Record<string, any>|null|undefined} details
 * @returns {Array<{ label: string, value: string }>}
 */
export function formatClientActivityDetails(details) {
	return formatAuditDetails(details);
}

/**
 * Staff route for an entity, or null when there is no useful page.
 * @param {string|null|undefined} entityType
 * @param {string|null|undefined} entityId
 * @returns {string|null}
 */
export function auditEntityHref(entityType, entityId) {
	if (!entityType || !entityId) return null;
	switch (entityType) {
		case 'project':
			return `/projects/${entityId}`;
		case 'invoice':
			return `/invoices/${entityId}`;
		case 'client':
			return `/clients/${entityId}`;
		case 'admin_user':
		case 'user':
			return '/team';
		default:
			return null;
	}
}
