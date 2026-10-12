// Only the Buffer operations used by the unmodified kit; no Node runtime.
class SsenBuffer extends Uint8Array {
 static from(value, encoding) {
  if (typeof value !== 'string') return new SsenBuffer(value);
  if (encoding === 'base64' || encoding === 'base64url') {
   const raw=atob(value.replace(/-/g,'+').replace(/_/g,'/'));
   return new SsenBuffer(Uint8Array.from(raw,c=>c.charCodeAt(0)));
  }
  return new SsenBuffer(new TextEncoder().encode(value));
 }
 toString(encoding='utf8') {
  if (encoding==='hex') return Array.from(this,b=>b.toString(16).padStart(2,'0')).join('');
  return new TextDecoder().decode(this);
 }
}
globalThis.Buffer=SsenBuffer;
