// Links this browser has created: the id and the owner token (needed to renew or revoke). Kept in localStorage;
// clearing the browser loses the ability to manage them.

export interface SharedLink {
  id: string;
  ownerToken: string;
  createdAt: string;
  expiresAt: string;
  count: number;
}

const KEY = "nyaya.sharedNotes.v1";

export function loadSharedLinks(): SharedLink[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SharedLink[]) : [];
  } catch {
    return [];
  }
}

export function saveSharedLinks(links: SharedLink[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(links));
  } catch {
    // storage unavailable: the link still works, but this browser cannot manage it later
  }
}

export function shareUrl(id: string): string {
  return `${window.location.origin}/notes/${id}`;
}
