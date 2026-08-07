const BASE_URL = "/api";

export async function verifyDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/verify`, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Verification failed (${res.status})`);
  }
  return res.json();
}

export async function listVerifications(verdict) {
  const url = verdict ? `${BASE_URL}/verifications?verdict=${verdict}` : `${BASE_URL}/verifications`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load verifications (${res.status})`);
  return res.json();
}

export async function getVerification(id) {
  const res = await fetch(`${BASE_URL}/verifications/${id}`);
  if (!res.ok) throw new Error(`Failed to load verification (${res.status})`);
  return res.json();
}

export async function reviewVerification(id, verdict) {
  const res = await fetch(`${BASE_URL}/verifications/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ verdict }),
  });
  if (!res.ok) throw new Error(`Failed to submit review (${res.status})`);
  return res.json();
}
