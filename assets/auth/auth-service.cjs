// ssen-auth-kit 1.0 — 쎈PDF 1.0.4 공통 인증 번들 기반. 바뀐 점: createAuthService(bridge, app) 앱 이름 인자, 앱 이름 검사 일반화, BRIDGE 안내 문구 일반화.
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// service.ts
var service_exports = {};
__export(service_exports, {
  createAuthService: () => createAuthService
});
module.exports = __toCommonJS(service_exports);

// node_modules/@noble/ed25519/index.js
var ed25519_CURVE = {
  p: 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffedn,
  n: 0x1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3edn,
  h: 8n,
  a: 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffecn,
  d: 0x52036cee2b6ffe738cc740797779e89800700a4d4141d8ab75eb4dca135978a3n,
  Gx: 0x216936d3cd6e53fec0a4e231fdd6dc5c692cc7609525a7b2c9562d608f25d51an,
  Gy: 0x6666666666666666666666666666666666666666666666666666666666666658n
};
var { p: P, n: N, Gx, Gy, a: _a, d: _d } = ed25519_CURVE;
var h = 8n;
var L = 32;
var L2 = 64;
var err = (m = "") => {
  throw new Error(m);
};
var isBig = (n) => typeof n === "bigint";
var isStr = (s) => typeof s === "string";
var isBytes = (a) => a instanceof Uint8Array || ArrayBuffer.isView(a) && a.constructor.name === "Uint8Array";
var abytes = (a, l) => !isBytes(a) || typeof l === "number" && l > 0 && a.length !== l ? err("Uint8Array expected") : a;
var u8n = (len) => new Uint8Array(len);
var u8fr = (buf) => Uint8Array.from(buf);
var padh = (n, pad) => n.toString(16).padStart(pad, "0");
var bytesToHex = (b) => Array.from(abytes(b)).map((e) => padh(e, 2)).join("");
var C = { _0: 48, _9: 57, A: 65, F: 70, a: 97, f: 102 };
var _ch = (ch) => {
  if (ch >= C._0 && ch <= C._9)
    return ch - C._0;
  if (ch >= C.A && ch <= C.F)
    return ch - (C.A - 10);
  if (ch >= C.a && ch <= C.f)
    return ch - (C.a - 10);
  return;
};
var hexToBytes = (hex2) => {
  const e = "hex invalid";
  if (!isStr(hex2))
    return err(e);
  const hl = hex2.length;
  const al = hl / 2;
  if (hl % 2)
    return err(e);
  const array = u8n(al);
  for (let ai = 0, hi = 0; ai < al; ai++, hi += 2) {
    const n1 = _ch(hex2.charCodeAt(hi));
    const n2 = _ch(hex2.charCodeAt(hi + 1));
    if (n1 === void 0 || n2 === void 0)
      return err(e);
    array[ai] = n1 * 16 + n2;
  }
  return array;
};
var toU8 = (a, len) => abytes(isStr(a) ? hexToBytes(a) : u8fr(abytes(a)), len);
var cr = () => globalThis?.crypto;
var subtle = () => cr()?.subtle ?? err("crypto.subtle must be defined");
var concatBytes = (...arrs) => {
  const r = u8n(arrs.reduce((sum, a) => sum + abytes(a).length, 0));
  let pad = 0;
  arrs.forEach((a) => {
    r.set(a, pad);
    pad += a.length;
  });
  return r;
};
var randomBytes = (len = L) => {
  const c = cr();
  return c.getRandomValues(u8n(len));
};
var big = BigInt;
var arange = (n, min, max, msg = "bad number: out of range") => isBig(n) && min <= n && n < max ? n : err(msg);
var M = (a, b = P) => {
  const r = a % b;
  return r >= 0n ? r : b + r;
};
var modN = (a) => M(a, N);
var invert = (num, md) => {
  if (num === 0n || md <= 0n)
    err("no inverse n=" + num + " mod=" + md);
  let a = M(num, md), b = md, x = 0n, y = 1n, u = 1n, v = 0n;
  while (a !== 0n) {
    const q = b / a, r = b % a;
    const m = x - u * q, n = y - v * q;
    b = a, a = r, x = u, y = v, u = m, v = n;
  }
  return b === 1n ? M(x, md) : err("no inverse");
};
var callHash = (name) => {
  const fn = etc[name];
  if (typeof fn !== "function")
    err("hashes." + name + " not set");
  return fn;
};
var apoint = (p) => p instanceof Point ? p : err("Point expected");
var B256 = 2n ** 256n;
var Point = class _Point {
  static BASE;
  static ZERO;
  ex;
  ey;
  ez;
  et;
  constructor(ex, ey, ez, et) {
    const max = B256;
    this.ex = arange(ex, 0n, max);
    this.ey = arange(ey, 0n, max);
    this.ez = arange(ez, 1n, max);
    this.et = arange(et, 0n, max);
    Object.freeze(this);
  }
  static fromAffine(p) {
    return new _Point(p.x, p.y, 1n, M(p.x * p.y));
  }
  /** RFC8032 5.1.3: Uint8Array to Point. */
  static fromBytes(hex2, zip215 = false) {
    const d = _d;
    const normed = u8fr(abytes(hex2, L));
    const lastByte = hex2[31];
    normed[31] = lastByte & ~128;
    const y = bytesToNumLE(normed);
    const max = zip215 ? B256 : P;
    arange(y, 0n, max);
    const y2 = M(y * y);
    const u = M(y2 - 1n);
    const v = M(d * y2 + 1n);
    let { isValid, value: x } = uvRatio(u, v);
    if (!isValid)
      err("bad point: y not sqrt");
    const isXOdd = (x & 1n) === 1n;
    const isLastByteOdd = (lastByte & 128) !== 0;
    if (!zip215 && x === 0n && isLastByteOdd)
      err("bad point: x==0, isLastByteOdd");
    if (isLastByteOdd !== isXOdd)
      x = M(-x);
    return new _Point(x, y, 1n, M(x * y));
  }
  /** Checks if the point is valid and on-curve. */
  assertValidity() {
    const a = _a;
    const d = _d;
    const p = this;
    if (p.is0())
      throw new Error("bad point: ZERO");
    const { ex: X, ey: Y, ez: Z, et: T } = p;
    const X2 = M(X * X);
    const Y2 = M(Y * Y);
    const Z2 = M(Z * Z);
    const Z4 = M(Z2 * Z2);
    const aX2 = M(X2 * a);
    const left = M(Z2 * M(aX2 + Y2));
    const right = M(Z4 + M(d * M(X2 * Y2)));
    if (left !== right)
      throw new Error("bad point: equation left != right (1)");
    const XY = M(X * Y);
    const ZT = M(Z * T);
    if (XY !== ZT)
      throw new Error("bad point: equation left != right (2)");
    return this;
  }
  /** Equality check: compare points P&Q. */
  equals(other) {
    const { ex: X1, ey: Y1, ez: Z1 } = this;
    const { ex: X2, ey: Y2, ez: Z2 } = apoint(other);
    const X1Z2 = M(X1 * Z2);
    const X2Z1 = M(X2 * Z1);
    const Y1Z2 = M(Y1 * Z2);
    const Y2Z1 = M(Y2 * Z1);
    return X1Z2 === X2Z1 && Y1Z2 === Y2Z1;
  }
  is0() {
    return this.equals(I);
  }
  /** Flip point over y coordinate. */
  negate() {
    return new _Point(M(-this.ex), this.ey, this.ez, M(-this.et));
  }
  /** Point doubling. Complete formula. Cost: `4M + 4S + 1*a + 6add + 1*2`. */
  double() {
    const { ex: X1, ey: Y1, ez: Z1 } = this;
    const a = _a;
    const A = M(X1 * X1);
    const B = M(Y1 * Y1);
    const C2 = M(2n * M(Z1 * Z1));
    const D = M(a * A);
    const x1y1 = X1 + Y1;
    const E = M(M(x1y1 * x1y1) - A - B);
    const G2 = D + B;
    const F = G2 - C2;
    const H = D - B;
    const X3 = M(E * F);
    const Y3 = M(G2 * H);
    const T3 = M(E * H);
    const Z3 = M(F * G2);
    return new _Point(X3, Y3, Z3, T3);
  }
  /** Point addition. Complete formula. Cost: `8M + 1*k + 8add + 1*2`. */
  add(other) {
    const { ex: X1, ey: Y1, ez: Z1, et: T1 } = this;
    const { ex: X2, ey: Y2, ez: Z2, et: T2 } = apoint(other);
    const a = _a;
    const d = _d;
    const A = M(X1 * X2);
    const B = M(Y1 * Y2);
    const C2 = M(T1 * d * T2);
    const D = M(Z1 * Z2);
    const E = M((X1 + Y1) * (X2 + Y2) - A - B);
    const F = M(D - C2);
    const G2 = M(D + C2);
    const H = M(B - a * A);
    const X3 = M(E * F);
    const Y3 = M(G2 * H);
    const T3 = M(E * H);
    const Z3 = M(F * G2);
    return new _Point(X3, Y3, Z3, T3);
  }
  /**
   * Point-by-scalar multiplication. Scalar must be in range 1 <= n < CURVE.n.
   * Uses {@link wNAF} for base point.
   * Uses fake point to mitigate side-channel leakage.
   * @param n scalar by which point is multiplied
   * @param safe safe mode guards against timing attacks; unsafe mode is faster
   */
  multiply(n, safe = true) {
    if (!safe && (n === 0n || this.is0()))
      return I;
    arange(n, 1n, N);
    if (n === 1n)
      return this;
    if (this.equals(G))
      return wNAF(n).p;
    let p = I;
    let f = G;
    for (let d = this; n > 0n; d = d.double(), n >>= 1n) {
      if (n & 1n)
        p = p.add(d);
      else if (safe)
        f = f.add(d);
    }
    return p;
  }
  /** Convert point to 2d xy affine point. (X, Y, Z) ∋ (x=X/Z, y=Y/Z) */
  toAffine() {
    const { ex: x, ey: y, ez: z } = this;
    if (this.equals(I))
      return { x: 0n, y: 1n };
    const iz = invert(z, P);
    if (M(z * iz) !== 1n)
      err("invalid inverse");
    return { x: M(x * iz), y: M(y * iz) };
  }
  toBytes() {
    const { x, y } = this.assertValidity().toAffine();
    const b = numTo32bLE(y);
    b[31] |= x & 1n ? 128 : 0;
    return b;
  }
  toHex() {
    return bytesToHex(this.toBytes());
  }
  // encode to hex string
  clearCofactor() {
    return this.multiply(big(h), false);
  }
  isSmallOrder() {
    return this.clearCofactor().is0();
  }
  isTorsionFree() {
    let p = this.multiply(N / 2n, false).double();
    if (N % 2n)
      p = p.add(this);
    return p.is0();
  }
  static fromHex(hex2, zip215) {
    return _Point.fromBytes(toU8(hex2), zip215);
  }
  get x() {
    return this.toAffine().x;
  }
  get y() {
    return this.toAffine().y;
  }
  toRawBytes() {
    return this.toBytes();
  }
};
var G = new Point(Gx, Gy, 1n, M(Gx * Gy));
var I = new Point(0n, 1n, 1n, 0n);
Point.BASE = G;
Point.ZERO = I;
var numTo32bLE = (num) => hexToBytes(padh(arange(num, 0n, B256), L2)).reverse();
var bytesToNumLE = (b) => big("0x" + bytesToHex(u8fr(abytes(b)).reverse()));
var pow2 = (x, power) => {
  let r = x;
  while (power-- > 0n) {
    r *= r;
    r %= P;
  }
  return r;
};
var pow_2_252_3 = (x) => {
  const x2 = x * x % P;
  const b2 = x2 * x % P;
  const b4 = pow2(b2, 2n) * b2 % P;
  const b5 = pow2(b4, 1n) * x % P;
  const b10 = pow2(b5, 5n) * b5 % P;
  const b20 = pow2(b10, 10n) * b10 % P;
  const b40 = pow2(b20, 20n) * b20 % P;
  const b80 = pow2(b40, 40n) * b40 % P;
  const b160 = pow2(b80, 80n) * b80 % P;
  const b240 = pow2(b160, 80n) * b80 % P;
  const b250 = pow2(b240, 10n) * b10 % P;
  const pow_p_5_8 = pow2(b250, 2n) * x % P;
  return { pow_p_5_8, b2 };
};
var RM1 = 0x2b8324804fc1df0b2b4d00993dfbd7a72f431806ad2fe478c4ee1b274a0ea0b0n;
var uvRatio = (u, v) => {
  const v3 = M(v * v * v);
  const v7 = M(v3 * v3 * v);
  const pow = pow_2_252_3(u * v7).pow_p_5_8;
  let x = M(u * v3 * pow);
  const vx2 = M(v * x * x);
  const root1 = x;
  const root2 = M(x * RM1);
  const useRoot1 = vx2 === u;
  const useRoot2 = vx2 === M(-u);
  const noRoot = vx2 === M(-u * RM1);
  if (useRoot1)
    x = root1;
  if (useRoot2 || noRoot)
    x = root2;
  if ((M(x) & 1n) === 1n)
    x = M(-x);
  return { isValid: useRoot1 || useRoot2, value: x };
};
var modL_LE = (hash) => modN(bytesToNumLE(hash));
var sha512a = (...m) => etc.sha512Async(...m);
var sha512s = (...m) => callHash("sha512Sync")(...m);
var hash2extK = (hashed) => {
  const head = hashed.slice(0, L);
  head[0] &= 248;
  head[31] &= 127;
  head[31] |= 64;
  const prefix = hashed.slice(L, L2);
  const scalar = modL_LE(head);
  const point = G.multiply(scalar);
  const pointBytes = point.toBytes();
  return { head, prefix, scalar, point, pointBytes };
};
var getExtendedPublicKeyAsync = (priv) => sha512a(toU8(priv, L)).then(hash2extK);
var getExtendedPublicKey = (priv) => hash2extK(sha512s(toU8(priv, L)));
var getPublicKey = (priv) => getExtendedPublicKey(priv).pointBytes;
var hashFinishS = (res) => res.finish(sha512s(res.hashable));
var _sign = (e, rBytes, msg) => {
  const { pointBytes: P2, scalar: s } = e;
  const r = modL_LE(rBytes);
  const R = G.multiply(r).toBytes();
  const hashable = concatBytes(R, P2, msg);
  const finish = (hashed) => {
    const S = modN(r + modL_LE(hashed) * s);
    return abytes(concatBytes(R, numTo32bLE(S)), L2);
  };
  return { hashable, finish };
};
var sign = (msg, privKey) => {
  const m = toU8(msg);
  const e = getExtendedPublicKey(privKey);
  const rBytes = sha512s(e.prefix, m);
  return hashFinishS(_sign(e, rBytes, m));
};
var veriOpts = { zip215: true };
var _verify = (sig, msg, pub, opts = veriOpts) => {
  sig = toU8(sig, L2);
  msg = toU8(msg);
  pub = toU8(pub, L);
  const { zip215 } = opts;
  let A;
  let R;
  let s;
  let SB;
  let hashable = Uint8Array.of();
  try {
    A = Point.fromHex(pub, zip215);
    R = Point.fromHex(sig.slice(0, L), zip215);
    s = bytesToNumLE(sig.slice(L, L2));
    SB = G.multiply(s, false);
    hashable = concatBytes(R.toBytes(), A.toBytes(), msg);
  } catch (error) {
  }
  const finish = (hashed) => {
    if (SB == null)
      return false;
    if (!zip215 && A.isSmallOrder())
      return false;
    const k = modL_LE(hashed);
    const RkA = R.add(A.multiply(k, false));
    return RkA.add(SB.negate()).clearCofactor().is0();
  };
  return { hashable, finish };
};
var verify = (s, m, p, opts = veriOpts) => hashFinishS(_verify(s, m, p, opts));
var etc = {
  sha512Async: async (...messages2) => {
    const s = subtle();
    const m = concatBytes(...messages2);
    return u8n(await s.digest("SHA-512", m.buffer));
  },
  sha512Sync: void 0,
  bytesToHex,
  hexToBytes,
  concatBytes,
  mod: M,
  invert,
  randomBytes
};
var utils = {
  getExtendedPublicKeyAsync,
  getExtendedPublicKey,
  randomPrivateKey: () => randomBytes(L),
  precompute: (w = 8, p = G) => {
    p.multiply(3n);
    w;
    return p;
  }
  // no-op
};
var W = 8;
var scalarBits = 256;
var pwindows = Math.ceil(scalarBits / W) + 1;
var pwindowSize = 2 ** (W - 1);
var precompute = () => {
  const points = [];
  let p = G;
  let b = p;
  for (let w = 0; w < pwindows; w++) {
    b = p;
    points.push(b);
    for (let i = 1; i < pwindowSize; i++) {
      b = b.add(p);
      points.push(b);
    }
    p = b.double();
  }
  return points;
};
var Gpows = void 0;
var ctneg = (cnd, p) => {
  const n = p.negate();
  return cnd ? n : p;
};
var wNAF = (n) => {
  const comp = Gpows || (Gpows = precompute());
  let p = I;
  let f = G;
  const pow_2_w = 2 ** W;
  const maxNum = pow_2_w;
  const mask = big(pow_2_w - 1);
  const shiftBy = big(W);
  for (let w = 0; w < pwindows; w++) {
    let wbits = Number(n & mask);
    n >>= shiftBy;
    if (wbits > pwindowSize) {
      wbits -= maxNum;
      n += 1n;
    }
    const off = w * pwindowSize;
    const offF = off;
    const offP = off + Math.abs(wbits) - 1;
    const isEven = w % 2 !== 0;
    const isNeg = wbits < 0;
    if (wbits === 0) {
      f = f.add(ctneg(isEven, comp[offF]));
    } else {
      p = p.add(ctneg(isNeg, comp[offP]));
    }
  }
  return { p, f };
};

// node_modules/@noble/hashes/esm/utils.js
function isBytes2(a) {
  return a instanceof Uint8Array || ArrayBuffer.isView(a) && a.constructor.name === "Uint8Array";
}
function abytes2(b, ...lengths) {
  if (!isBytes2(b))
    throw new Error("Uint8Array expected");
  if (lengths.length > 0 && !lengths.includes(b.length))
    throw new Error("Uint8Array expected of length " + lengths + ", got length=" + b.length);
}
function aexists(instance, checkFinished = true) {
  if (instance.destroyed)
    throw new Error("Hash instance has been destroyed");
  if (checkFinished && instance.finished)
    throw new Error("Hash#digest() has already been called");
}
function aoutput(out, instance) {
  abytes2(out);
  const min = instance.outputLen;
  if (out.length < min) {
    throw new Error("digestInto() expects output buffer of length at least " + min);
  }
}
function clean(...arrays) {
  for (let i = 0; i < arrays.length; i++) {
    arrays[i].fill(0);
  }
}
function createView(arr) {
  return new DataView(arr.buffer, arr.byteOffset, arr.byteLength);
}
function rotr(word, shift) {
  return word << 32 - shift | word >>> shift;
}
function utf8ToBytes(str) {
  if (typeof str !== "string")
    throw new Error("string expected");
  return new Uint8Array(new TextEncoder().encode(str));
}
function toBytes(data) {
  if (typeof data === "string")
    data = utf8ToBytes(data);
  abytes2(data);
  return data;
}
var Hash = class {
};
function createHasher(hashCons) {
  const hashC = (msg) => hashCons().update(toBytes(msg)).digest();
  const tmp = hashCons();
  hashC.outputLen = tmp.outputLen;
  hashC.blockLen = tmp.blockLen;
  hashC.create = () => hashCons();
  return hashC;
}

// node_modules/@noble/hashes/esm/_md.js
function setBigUint64(view, byteOffset, value, isLE) {
  if (typeof view.setBigUint64 === "function")
    return view.setBigUint64(byteOffset, value, isLE);
  const _32n2 = BigInt(32);
  const _u32_max = BigInt(4294967295);
  const wh = Number(value >> _32n2 & _u32_max);
  const wl = Number(value & _u32_max);
  const h2 = isLE ? 4 : 0;
  const l = isLE ? 0 : 4;
  view.setUint32(byteOffset + h2, wh, isLE);
  view.setUint32(byteOffset + l, wl, isLE);
}
function Chi(a, b, c) {
  return a & b ^ ~a & c;
}
function Maj(a, b, c) {
  return a & b ^ a & c ^ b & c;
}
var HashMD = class extends Hash {
  constructor(blockLen, outputLen, padOffset, isLE) {
    super();
    this.finished = false;
    this.length = 0;
    this.pos = 0;
    this.destroyed = false;
    this.blockLen = blockLen;
    this.outputLen = outputLen;
    this.padOffset = padOffset;
    this.isLE = isLE;
    this.buffer = new Uint8Array(blockLen);
    this.view = createView(this.buffer);
  }
  update(data) {
    aexists(this);
    data = toBytes(data);
    abytes2(data);
    const { view, buffer, blockLen } = this;
    const len = data.length;
    for (let pos = 0; pos < len; ) {
      const take = Math.min(blockLen - this.pos, len - pos);
      if (take === blockLen) {
        const dataView = createView(data);
        for (; blockLen <= len - pos; pos += blockLen)
          this.process(dataView, pos);
        continue;
      }
      buffer.set(data.subarray(pos, pos + take), this.pos);
      this.pos += take;
      pos += take;
      if (this.pos === blockLen) {
        this.process(view, 0);
        this.pos = 0;
      }
    }
    this.length += data.length;
    this.roundClean();
    return this;
  }
  digestInto(out) {
    aexists(this);
    aoutput(out, this);
    this.finished = true;
    const { buffer, view, blockLen, isLE } = this;
    let { pos } = this;
    buffer[pos++] = 128;
    clean(this.buffer.subarray(pos));
    if (this.padOffset > blockLen - pos) {
      this.process(view, 0);
      pos = 0;
    }
    for (let i = pos; i < blockLen; i++)
      buffer[i] = 0;
    setBigUint64(view, blockLen - 8, BigInt(this.length * 8), isLE);
    this.process(view, 0);
    const oview = createView(out);
    const len = this.outputLen;
    if (len % 4)
      throw new Error("_sha2: outputLen should be aligned to 32bit");
    const outLen = len / 4;
    const state = this.get();
    if (outLen > state.length)
      throw new Error("_sha2: outputLen bigger than state");
    for (let i = 0; i < outLen; i++)
      oview.setUint32(4 * i, state[i], isLE);
  }
  digest() {
    const { buffer, outputLen } = this;
    this.digestInto(buffer);
    const res = buffer.slice(0, outputLen);
    this.destroy();
    return res;
  }
  _cloneInto(to) {
    to || (to = new this.constructor());
    to.set(...this.get());
    const { blockLen, buffer, length, finished, destroyed, pos } = this;
    to.destroyed = destroyed;
    to.finished = finished;
    to.length = length;
    to.pos = pos;
    if (length % blockLen)
      to.buffer.set(buffer);
    return to;
  }
  clone() {
    return this._cloneInto();
  }
};
var SHA256_IV = /* @__PURE__ */ Uint32Array.from([
  1779033703,
  3144134277,
  1013904242,
  2773480762,
  1359893119,
  2600822924,
  528734635,
  1541459225
]);
var SHA512_IV = /* @__PURE__ */ Uint32Array.from([
  1779033703,
  4089235720,
  3144134277,
  2227873595,
  1013904242,
  4271175723,
  2773480762,
  1595750129,
  1359893119,
  2917565137,
  2600822924,
  725511199,
  528734635,
  4215389547,
  1541459225,
  327033209
]);

// node_modules/@noble/hashes/esm/_u64.js
var U32_MASK64 = /* @__PURE__ */ BigInt(2 ** 32 - 1);
var _32n = /* @__PURE__ */ BigInt(32);
function fromBig(n, le = false) {
  if (le)
    return { h: Number(n & U32_MASK64), l: Number(n >> _32n & U32_MASK64) };
  return { h: Number(n >> _32n & U32_MASK64) | 0, l: Number(n & U32_MASK64) | 0 };
}
function split(lst, le = false) {
  const len = lst.length;
  let Ah = new Uint32Array(len);
  let Al = new Uint32Array(len);
  for (let i = 0; i < len; i++) {
    const { h: h2, l } = fromBig(lst[i], le);
    [Ah[i], Al[i]] = [h2, l];
  }
  return [Ah, Al];
}
var shrSH = (h2, _l, s) => h2 >>> s;
var shrSL = (h2, l, s) => h2 << 32 - s | l >>> s;
var rotrSH = (h2, l, s) => h2 >>> s | l << 32 - s;
var rotrSL = (h2, l, s) => h2 << 32 - s | l >>> s;
var rotrBH = (h2, l, s) => h2 << 64 - s | l >>> s - 32;
var rotrBL = (h2, l, s) => h2 >>> s - 32 | l << 64 - s;
function add(Ah, Al, Bh, Bl) {
  const l = (Al >>> 0) + (Bl >>> 0);
  return { h: Ah + Bh + (l / 2 ** 32 | 0) | 0, l: l | 0 };
}
var add3L = (Al, Bl, Cl) => (Al >>> 0) + (Bl >>> 0) + (Cl >>> 0);
var add3H = (low, Ah, Bh, Ch) => Ah + Bh + Ch + (low / 2 ** 32 | 0) | 0;
var add4L = (Al, Bl, Cl, Dl) => (Al >>> 0) + (Bl >>> 0) + (Cl >>> 0) + (Dl >>> 0);
var add4H = (low, Ah, Bh, Ch, Dh) => Ah + Bh + Ch + Dh + (low / 2 ** 32 | 0) | 0;
var add5L = (Al, Bl, Cl, Dl, El) => (Al >>> 0) + (Bl >>> 0) + (Cl >>> 0) + (Dl >>> 0) + (El >>> 0);
var add5H = (low, Ah, Bh, Ch, Dh, Eh) => Ah + Bh + Ch + Dh + Eh + (low / 2 ** 32 | 0) | 0;

// node_modules/@noble/hashes/esm/sha2.js
var SHA256_K = /* @__PURE__ */ Uint32Array.from([
  1116352408,
  1899447441,
  3049323471,
  3921009573,
  961987163,
  1508970993,
  2453635748,
  2870763221,
  3624381080,
  310598401,
  607225278,
  1426881987,
  1925078388,
  2162078206,
  2614888103,
  3248222580,
  3835390401,
  4022224774,
  264347078,
  604807628,
  770255983,
  1249150122,
  1555081692,
  1996064986,
  2554220882,
  2821834349,
  2952996808,
  3210313671,
  3336571891,
  3584528711,
  113926993,
  338241895,
  666307205,
  773529912,
  1294757372,
  1396182291,
  1695183700,
  1986661051,
  2177026350,
  2456956037,
  2730485921,
  2820302411,
  3259730800,
  3345764771,
  3516065817,
  3600352804,
  4094571909,
  275423344,
  430227734,
  506948616,
  659060556,
  883997877,
  958139571,
  1322822218,
  1537002063,
  1747873779,
  1955562222,
  2024104815,
  2227730452,
  2361852424,
  2428436474,
  2756734187,
  3204031479,
  3329325298
]);
var SHA256_W = /* @__PURE__ */ new Uint32Array(64);
var SHA256 = class extends HashMD {
  constructor(outputLen = 32) {
    super(64, outputLen, 8, false);
    this.A = SHA256_IV[0] | 0;
    this.B = SHA256_IV[1] | 0;
    this.C = SHA256_IV[2] | 0;
    this.D = SHA256_IV[3] | 0;
    this.E = SHA256_IV[4] | 0;
    this.F = SHA256_IV[5] | 0;
    this.G = SHA256_IV[6] | 0;
    this.H = SHA256_IV[7] | 0;
  }
  get() {
    const { A, B, C: C2, D, E, F, G: G2, H } = this;
    return [A, B, C2, D, E, F, G2, H];
  }
  // prettier-ignore
  set(A, B, C2, D, E, F, G2, H) {
    this.A = A | 0;
    this.B = B | 0;
    this.C = C2 | 0;
    this.D = D | 0;
    this.E = E | 0;
    this.F = F | 0;
    this.G = G2 | 0;
    this.H = H | 0;
  }
  process(view, offset) {
    for (let i = 0; i < 16; i++, offset += 4)
      SHA256_W[i] = view.getUint32(offset, false);
    for (let i = 16; i < 64; i++) {
      const W15 = SHA256_W[i - 15];
      const W2 = SHA256_W[i - 2];
      const s0 = rotr(W15, 7) ^ rotr(W15, 18) ^ W15 >>> 3;
      const s1 = rotr(W2, 17) ^ rotr(W2, 19) ^ W2 >>> 10;
      SHA256_W[i] = s1 + SHA256_W[i - 7] + s0 + SHA256_W[i - 16] | 0;
    }
    let { A, B, C: C2, D, E, F, G: G2, H } = this;
    for (let i = 0; i < 64; i++) {
      const sigma1 = rotr(E, 6) ^ rotr(E, 11) ^ rotr(E, 25);
      const T1 = H + sigma1 + Chi(E, F, G2) + SHA256_K[i] + SHA256_W[i] | 0;
      const sigma0 = rotr(A, 2) ^ rotr(A, 13) ^ rotr(A, 22);
      const T2 = sigma0 + Maj(A, B, C2) | 0;
      H = G2;
      G2 = F;
      F = E;
      E = D + T1 | 0;
      D = C2;
      C2 = B;
      B = A;
      A = T1 + T2 | 0;
    }
    A = A + this.A | 0;
    B = B + this.B | 0;
    C2 = C2 + this.C | 0;
    D = D + this.D | 0;
    E = E + this.E | 0;
    F = F + this.F | 0;
    G2 = G2 + this.G | 0;
    H = H + this.H | 0;
    this.set(A, B, C2, D, E, F, G2, H);
  }
  roundClean() {
    clean(SHA256_W);
  }
  destroy() {
    this.set(0, 0, 0, 0, 0, 0, 0, 0);
    clean(this.buffer);
  }
};
var K512 = /* @__PURE__ */ (() => split([
  "0x428a2f98d728ae22",
  "0x7137449123ef65cd",
  "0xb5c0fbcfec4d3b2f",
  "0xe9b5dba58189dbbc",
  "0x3956c25bf348b538",
  "0x59f111f1b605d019",
  "0x923f82a4af194f9b",
  "0xab1c5ed5da6d8118",
  "0xd807aa98a3030242",
  "0x12835b0145706fbe",
  "0x243185be4ee4b28c",
  "0x550c7dc3d5ffb4e2",
  "0x72be5d74f27b896f",
  "0x80deb1fe3b1696b1",
  "0x9bdc06a725c71235",
  "0xc19bf174cf692694",
  "0xe49b69c19ef14ad2",
  "0xefbe4786384f25e3",
  "0x0fc19dc68b8cd5b5",
  "0x240ca1cc77ac9c65",
  "0x2de92c6f592b0275",
  "0x4a7484aa6ea6e483",
  "0x5cb0a9dcbd41fbd4",
  "0x76f988da831153b5",
  "0x983e5152ee66dfab",
  "0xa831c66d2db43210",
  "0xb00327c898fb213f",
  "0xbf597fc7beef0ee4",
  "0xc6e00bf33da88fc2",
  "0xd5a79147930aa725",
  "0x06ca6351e003826f",
  "0x142929670a0e6e70",
  "0x27b70a8546d22ffc",
  "0x2e1b21385c26c926",
  "0x4d2c6dfc5ac42aed",
  "0x53380d139d95b3df",
  "0x650a73548baf63de",
  "0x766a0abb3c77b2a8",
  "0x81c2c92e47edaee6",
  "0x92722c851482353b",
  "0xa2bfe8a14cf10364",
  "0xa81a664bbc423001",
  "0xc24b8b70d0f89791",
  "0xc76c51a30654be30",
  "0xd192e819d6ef5218",
  "0xd69906245565a910",
  "0xf40e35855771202a",
  "0x106aa07032bbd1b8",
  "0x19a4c116b8d2d0c8",
  "0x1e376c085141ab53",
  "0x2748774cdf8eeb99",
  "0x34b0bcb5e19b48a8",
  "0x391c0cb3c5c95a63",
  "0x4ed8aa4ae3418acb",
  "0x5b9cca4f7763e373",
  "0x682e6ff3d6b2b8a3",
  "0x748f82ee5defb2fc",
  "0x78a5636f43172f60",
  "0x84c87814a1f0ab72",
  "0x8cc702081a6439ec",
  "0x90befffa23631e28",
  "0xa4506cebde82bde9",
  "0xbef9a3f7b2c67915",
  "0xc67178f2e372532b",
  "0xca273eceea26619c",
  "0xd186b8c721c0c207",
  "0xeada7dd6cde0eb1e",
  "0xf57d4f7fee6ed178",
  "0x06f067aa72176fba",
  "0x0a637dc5a2c898a6",
  "0x113f9804bef90dae",
  "0x1b710b35131c471b",
  "0x28db77f523047d84",
  "0x32caab7b40c72493",
  "0x3c9ebe0a15c9bebc",
  "0x431d67c49c100d4c",
  "0x4cc5d4becb3e42b6",
  "0x597f299cfc657e2a",
  "0x5fcb6fab3ad6faec",
  "0x6c44198c4a475817"
].map((n) => BigInt(n))))();
var SHA512_Kh = /* @__PURE__ */ (() => K512[0])();
var SHA512_Kl = /* @__PURE__ */ (() => K512[1])();
var SHA512_W_H = /* @__PURE__ */ new Uint32Array(80);
var SHA512_W_L = /* @__PURE__ */ new Uint32Array(80);
var SHA512 = class extends HashMD {
  constructor(outputLen = 64) {
    super(128, outputLen, 16, false);
    this.Ah = SHA512_IV[0] | 0;
    this.Al = SHA512_IV[1] | 0;
    this.Bh = SHA512_IV[2] | 0;
    this.Bl = SHA512_IV[3] | 0;
    this.Ch = SHA512_IV[4] | 0;
    this.Cl = SHA512_IV[5] | 0;
    this.Dh = SHA512_IV[6] | 0;
    this.Dl = SHA512_IV[7] | 0;
    this.Eh = SHA512_IV[8] | 0;
    this.El = SHA512_IV[9] | 0;
    this.Fh = SHA512_IV[10] | 0;
    this.Fl = SHA512_IV[11] | 0;
    this.Gh = SHA512_IV[12] | 0;
    this.Gl = SHA512_IV[13] | 0;
    this.Hh = SHA512_IV[14] | 0;
    this.Hl = SHA512_IV[15] | 0;
  }
  // prettier-ignore
  get() {
    const { Ah, Al, Bh, Bl, Ch, Cl, Dh, Dl, Eh, El, Fh, Fl, Gh, Gl, Hh, Hl } = this;
    return [Ah, Al, Bh, Bl, Ch, Cl, Dh, Dl, Eh, El, Fh, Fl, Gh, Gl, Hh, Hl];
  }
  // prettier-ignore
  set(Ah, Al, Bh, Bl, Ch, Cl, Dh, Dl, Eh, El, Fh, Fl, Gh, Gl, Hh, Hl) {
    this.Ah = Ah | 0;
    this.Al = Al | 0;
    this.Bh = Bh | 0;
    this.Bl = Bl | 0;
    this.Ch = Ch | 0;
    this.Cl = Cl | 0;
    this.Dh = Dh | 0;
    this.Dl = Dl | 0;
    this.Eh = Eh | 0;
    this.El = El | 0;
    this.Fh = Fh | 0;
    this.Fl = Fl | 0;
    this.Gh = Gh | 0;
    this.Gl = Gl | 0;
    this.Hh = Hh | 0;
    this.Hl = Hl | 0;
  }
  process(view, offset) {
    for (let i = 0; i < 16; i++, offset += 4) {
      SHA512_W_H[i] = view.getUint32(offset);
      SHA512_W_L[i] = view.getUint32(offset += 4);
    }
    for (let i = 16; i < 80; i++) {
      const W15h = SHA512_W_H[i - 15] | 0;
      const W15l = SHA512_W_L[i - 15] | 0;
      const s0h = rotrSH(W15h, W15l, 1) ^ rotrSH(W15h, W15l, 8) ^ shrSH(W15h, W15l, 7);
      const s0l = rotrSL(W15h, W15l, 1) ^ rotrSL(W15h, W15l, 8) ^ shrSL(W15h, W15l, 7);
      const W2h = SHA512_W_H[i - 2] | 0;
      const W2l = SHA512_W_L[i - 2] | 0;
      const s1h = rotrSH(W2h, W2l, 19) ^ rotrBH(W2h, W2l, 61) ^ shrSH(W2h, W2l, 6);
      const s1l = rotrSL(W2h, W2l, 19) ^ rotrBL(W2h, W2l, 61) ^ shrSL(W2h, W2l, 6);
      const SUMl = add4L(s0l, s1l, SHA512_W_L[i - 7], SHA512_W_L[i - 16]);
      const SUMh = add4H(SUMl, s0h, s1h, SHA512_W_H[i - 7], SHA512_W_H[i - 16]);
      SHA512_W_H[i] = SUMh | 0;
      SHA512_W_L[i] = SUMl | 0;
    }
    let { Ah, Al, Bh, Bl, Ch, Cl, Dh, Dl, Eh, El, Fh, Fl, Gh, Gl, Hh, Hl } = this;
    for (let i = 0; i < 80; i++) {
      const sigma1h = rotrSH(Eh, El, 14) ^ rotrSH(Eh, El, 18) ^ rotrBH(Eh, El, 41);
      const sigma1l = rotrSL(Eh, El, 14) ^ rotrSL(Eh, El, 18) ^ rotrBL(Eh, El, 41);
      const CHIh = Eh & Fh ^ ~Eh & Gh;
      const CHIl = El & Fl ^ ~El & Gl;
      const T1ll = add5L(Hl, sigma1l, CHIl, SHA512_Kl[i], SHA512_W_L[i]);
      const T1h = add5H(T1ll, Hh, sigma1h, CHIh, SHA512_Kh[i], SHA512_W_H[i]);
      const T1l = T1ll | 0;
      const sigma0h = rotrSH(Ah, Al, 28) ^ rotrBH(Ah, Al, 34) ^ rotrBH(Ah, Al, 39);
      const sigma0l = rotrSL(Ah, Al, 28) ^ rotrBL(Ah, Al, 34) ^ rotrBL(Ah, Al, 39);
      const MAJh = Ah & Bh ^ Ah & Ch ^ Bh & Ch;
      const MAJl = Al & Bl ^ Al & Cl ^ Bl & Cl;
      Hh = Gh | 0;
      Hl = Gl | 0;
      Gh = Fh | 0;
      Gl = Fl | 0;
      Fh = Eh | 0;
      Fl = El | 0;
      ({ h: Eh, l: El } = add(Dh | 0, Dl | 0, T1h | 0, T1l | 0));
      Dh = Ch | 0;
      Dl = Cl | 0;
      Ch = Bh | 0;
      Cl = Bl | 0;
      Bh = Ah | 0;
      Bl = Al | 0;
      const All = add3L(T1l, sigma0l, MAJl);
      Ah = add3H(All, T1h, sigma0h, MAJh);
      Al = All | 0;
    }
    ({ h: Ah, l: Al } = add(this.Ah | 0, this.Al | 0, Ah | 0, Al | 0));
    ({ h: Bh, l: Bl } = add(this.Bh | 0, this.Bl | 0, Bh | 0, Bl | 0));
    ({ h: Ch, l: Cl } = add(this.Ch | 0, this.Cl | 0, Ch | 0, Cl | 0));
    ({ h: Dh, l: Dl } = add(this.Dh | 0, this.Dl | 0, Dh | 0, Dl | 0));
    ({ h: Eh, l: El } = add(this.Eh | 0, this.El | 0, Eh | 0, El | 0));
    ({ h: Fh, l: Fl } = add(this.Fh | 0, this.Fl | 0, Fh | 0, Fl | 0));
    ({ h: Gh, l: Gl } = add(this.Gh | 0, this.Gl | 0, Gh | 0, Gl | 0));
    ({ h: Hh, l: Hl } = add(this.Hh | 0, this.Hl | 0, Hh | 0, Hl | 0));
    this.set(Ah, Al, Bh, Bl, Ch, Cl, Dh, Dl, Eh, El, Fh, Fl, Gh, Gl, Hh, Hl);
  }
  roundClean() {
    clean(SHA512_W_H, SHA512_W_L);
  }
  destroy() {
    clean(this.buffer);
    this.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
  }
};
var sha256 = /* @__PURE__ */ createHasher(() => new SHA256());
var sha512 = /* @__PURE__ */ createHasher(() => new SHA512());

// node_modules/@noble/hashes/esm/sha512.js
var sha5122 = sha512;

// node_modules/@noble/hashes/esm/sha256.js
var sha2562 = sha256;

// verify.ts
etc.sha512Sync = (...m) => sha5122(etc.concatBytes(...m));
var enc = new TextEncoder();
var B64URL = /^[A-Za-z0-9_-]+$/;
var d64 = (s) => new Uint8Array(Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64"));
var hex = (b) => Buffer.from(b).toString("hex");
function part(s) {
  return JSON.parse(Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8"));
}
function split3(jws) {
  if (typeof jws !== "string") return null;
  const a = jws.split(".");
  if (a.length !== 3 || a.some((x) => !x || !B64URL.test(x))) return null;
  return a;
}
function sigOk(x, h2, p, s) {
  try {
    const pub = d64(x), sig = d64(s);
    return pub.length === 32 && sig.length === 64 && verify(sig, enc.encode(h2 + "." + p), pub);
  } catch {
    return false;
  }
}
var isInt = (v) => typeof v === "number" && Number.isSafeInteger(v);
var isStr2 = (v) => typeof v === "string" && v.length > 0;
var emptyCache = () => ({ seq: 0, listHash: "", keys: [], revoked: [] });
function acceptKeyList(jws, trust, now, cache) {
  const no = (reason) => ({ ok: false, reason, cache });
  const s = split3(jws);
  if (!s) return no("KEYLIST_FORMAT");
  const [h2, p, g] = s;
  let hd, c;
  try {
    hd = part(h2);
  } catch {
    return no("KEYLIST_FORMAT");
  }
  if (hd?.alg !== "EdDSA" || hd?.typ !== "ssen-keys+jws" || hd?.kid !== trust.rootKid) return no("KEYLIST_HEADER");
  if (!sigOk(trust.rootX, h2, p, g)) return no("KEYLIST_SIGNATURE");
  try {
    c = part(p);
  } catch {
    return no("KEYLIST_FORMAT");
  }
  if (c?.v !== 2 || c?.typ !== "ssen-keys" || c?.iss !== trust.iss || !isInt(c?.iat) || !isInt(c?.exp) || !isInt(c?.seq) || !Array.isArray(c?.keys) || !Array.isArray(c?.revoked)) return no("KEYLIST_CLAIMS");
  if (now >= c.exp) return no("KEYLIST_EXPIRED");
  const listHash = hex(sha2562(enc.encode(p)));
  if (c.seq < cache.seq) return no("KEYLIST_ROLLBACK");
  if (c.seq === cache.seq) return listHash === cache.listHash ? { ok: true, cache, changed: false } : no("KEYLIST_CONFLICT");
  const keys = [];
  for (const k of c.keys) {
    if (!isStr2(k?.kid) || !isStr2(k?.x) || k?.alg !== "Ed25519" || !["active", "retired"].includes(k?.status)) return no("KEYLIST_CLAIMS");
    keys.push({ kid: k.kid, x: k.x, status: k.status });
  }
  const revoked = new Set(cache.revoked);
  for (const r of c.revoked) {
    if (!isStr2(r?.kid)) return no("KEYLIST_CLAIMS");
    revoked.add(r.kid);
  }
  return { ok: true, changed: true, cache: { seq: c.seq, listHash, keys: keys.filter((k) => !revoked.has(k.kid)), revoked: [...revoked] } };
}
var SKEW = 300;
function verifyLicense(token, cache, now, expect) {
  if (!expect || !isStr2(expect.iss) || !isStr2(expect.sub) || !isStr2(expect.regId) || !isStr2(expect.deviceId) || !/^[a-z][a-z0-9]{1,15}$/.test(expect.app) || !isInt(now)) return "ARGS";
  const s = split3(token);
  if (!s) return "FORMAT";
  const [h2, p, g] = s;
  let hd;
  try {
    hd = part(h2);
  } catch {
    return "FORMAT";
  }
  if (hd?.alg !== "EdDSA" || hd?.typ !== "ssen-lic+jwt" || !isStr2(hd?.kid)) return "HEADER";
  if (cache.revoked.includes(hd.kid)) return "REVOKED_KID";
  const k = cache.keys.find((x) => x.kid === hd.kid);
  if (!k) return "UNKNOWN_KID";
  if (!sigOk(k.x, h2, p, g)) return "BAD_SIGNATURE";
  let c;
  try {
    c = part(p);
  } catch {
    return "FORMAT";
  }
  const okTypes = c && c.v === 2 && isStr2(c.iss) && isStr2(c.aud) && c.typ === "general" && isStr2(c.sub) && isStr2(c.reg_id) && isStr2(c.device_id) && (c.plan === "trial" || c.plan === "licensed" || c.plan === "edu_free") && (c.license_id === null || isStr2(c.license_id)) && Array.isArray(c.scope) && c.scope.every(isStr2) && isInt(c.iat) && isInt(c.nbf) && isInt(c.refresh_at) && isInt(c.offline_until) && isInt(c.exp) && (c.ent_exp === null || isInt(c.ent_exp)) && isStr2(c.jti) && (c.plan === "licensed" ? c.license_id !== null : c.license_id === null) && (c.plan === "trial" || c.ent_exp !== null || c.plan === "licensed");
  if (!okTypes) return "CLAIMS";
  if (c.iss !== expect.iss) return "ISS";
  if (c.aud !== "ssen-desktop") return "AUD";
  if (c.sub !== expect.sub) return "SUBJECT";
  if (c.reg_id !== expect.regId || c.device_id !== expect.deviceId) return "DEVICE";
  if (!c.scope.includes(expect.app)) return "SCOPE";
  if (!(c.iat <= c.nbf && c.nbf <= c.refresh_at && c.refresh_at <= c.offline_until && c.offline_until <= c.exp)) return "TIMES";
  if (c.ent_exp !== null && c.exp > c.ent_exp) return "TIMES";
  if (now + SKEW < c.nbf) return "NOT_YET_VALID";
  if (c.ent_exp !== null && now >= c.ent_exp) return "ENT_EXPIRED";
  if (now >= c.exp) return "EXPIRED";
  if (now >= c.offline_until) return "OFFLINE_GRACE";
  return "OK";
}
function canonicalV3(method, pathAndQuery, nonce, regId, bearer, rawBody) {
  const sha = (t) => hex(sha2562(enc.encode(t)));
  return `SSEN-REQ-V3
${method.toUpperCase()}
${pathAndQuery}
${nonce}
${regId || "-"}
${bearer ? sha(bearer) : "-"}
${sha(rawBody)}`;
}

// client.ts
var ISS = "https://ssenbox.lovable.app";
var TRUST = { iss: ISS, rootKid: "6bc462d1500f496a", rootX: "QT5QC-vnrUrzaV6-GH-SfZGwH4ZMrnjPs7jMi2f197E" };
var enc2 = new TextEncoder();
var b64 = (b) => btoa(String.fromCharCode(...b)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
var un64 = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
var messages = { NETWORK: "\uC778\uC99D \uC11C\uBC84\uC5D0 \uC5F0\uACB0\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC778\uD130\uB137 \uC5F0\uACB0\uC744 \uD655\uC778\uD574 \uC8FC\uC138\uC694.", BAD_EMAIL: "\uC774\uBA54\uC77C \uC8FC\uC18C\uB97C \uD655\uC778\uD574 \uC8FC\uC138\uC694.", OTP_WRONG: "\uC778\uC99D\uBC88\uD638\uAC00 \uB9DE\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.", OTP_EXPIRED: "\uC778\uC99D\uBC88\uD638\uAC00 \uB9CC\uB8CC\uB410\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uBC1B\uC544 \uC8FC\uC138\uC694.", OTP_LOCKED: "\uC785\uB825 \uD69F\uC218\uB97C \uCD08\uACFC\uD588\uC2B5\uB2C8\uB2E4. \uC778\uC99D\uBC88\uD638\uB97C \uB2E4\uC2DC \uBC1B\uC544 \uC8FC\uC138\uC694.", TOO_SOON: "\uC7A0\uC2DC \uAE30\uB2E4\uB9B0 \uB4A4 \uC778\uC99D\uBC88\uD638\uB97C \uB2E4\uC2DC \uBC1B\uC544 \uC8FC\uC138\uC694.", MAIL_UNAVAILABLE: "\uBA54\uC77C \uBC1C\uC1A1\uC744 \uC900\uBE44 \uC911\uC785\uB2C8\uB2E4. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694.", DEVICE_LIMIT: "\uB4F1\uB85D \uAC00\uB2A5\uD55C PC \uC218\uB97C \uCD08\uACFC\uD588\uC2B5\uB2C8\uB2E4. \uC0AC\uC6A9\uD558\uC9C0 \uC54A\uB294 PC\uC758 \uC778\uC99D\uC744 \uD574\uC81C\uD574 \uC8FC\uC138\uC694.", ACCOUNT_SUSPENDED: "\uACC4\uC815 \uC774\uC6A9\uC774 \uC815\uC9C0\uB410\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790\uC5D0\uAC8C \uBB38\uC758\uD574 \uC8FC\uC138\uC694.", LICENSE_REVOKED: "\uC774\uC6A9\uAD8C\uC774 \uC815\uC9C0\uB410\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790\uC5D0\uAC8C \uBB38\uC758\uD574 \uC8FC\uC138\uC694.", LICENSE_EXPIRED: "\uC774\uC6A9 \uAE30\uAC04\uC774 \uB05D\uB0AC\uC2B5\uB2C8\uB2E4. \uAE30\uC874 \uC791\uC5C5\uC744 \uC5F4\uACE0 \uC800\uC7A5\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.", TRIAL_EXPIRED: "\uBB34\uB8CC \uCCB4\uD5D8\uC774 \uB05D\uB0AC\uC2B5\uB2C8\uB2E4. \uAE30\uC874 \uC791\uC5C5\uC744 \uC5F4\uACE0 \uC800\uC7A5\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.", LICENSE_UNREGISTERED: "\uBA54\uC77C\uB85C \uBC1B\uC740 \uC774\uC6A9\uAD8C \uCF54\uB4DC \uB610\uB294 \uB4F1\uB85D \uB9C1\uD06C\uB85C \uB4F1\uB85D\uC744 \uC644\uB8CC\uD574 \uC8FC\uC138\uC694.", TRIAL_NOT_STARTED: "90\uC77C \uBB34\uB8CC \uCCB4\uD5D8\uC744 \uC2DC\uC791\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.", DEVICE_DEACTIVATED: "\uC774 PC\uC758 \uC778\uC99D\uC774 \uD574\uC81C\uB410\uC2B5\uB2C8\uB2E4. \uC774\uBA54\uC77C \uC778\uC99D \uD6C4 \uB2E4\uC2DC \uB4F1\uB85D\uD574 \uC8FC\uC138\uC694.", BAD_SIGNATURE: "PC \uC778\uC99D \uD0A4\uAC00 \uBCC0\uACBD\uB410\uC2B5\uB2C8\uB2E4. \uC774\uBA54\uC77C \uC778\uC99D \uD6C4 \uB2E4\uC2DC \uB4F1\uB85D\uD574 \uC8FC\uC138\uC694.", KEY_REPLACE_REQUIRES_REAUTH: "\uC774\uBA54\uC77C \uC778\uC99D\uC744 \uB2E4\uC2DC \uBC1B\uC740 \uB4A4 PC\uB97C \uB4F1\uB85D\uD574 \uC8FC\uC138\uC694.", UNAUTHORIZED: "\uC11C\uBC84\uAC00 \uACC4\uC815 \uC778\uC99D\uC744 \uAC70\uC808\uD588\uC2B5\uB2C8\uB2E4. \uD1A0\uD070 \uB204\uB77D\xB7\uBCC0\uACBD \uB610\uB294 \uB9CC\uB8CC \uC5EC\uBD80\uB97C \uC9C4\uB2E8 \uC815\uBCF4\uC5D0\uC11C \uD655\uC778\uD574 \uC8FC\uC138\uC694.", STORE_CORRUPT: "\uBCF4\uC548 \uC800\uC7A5 \uC815\uBCF4\uB97C \uC77D\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. Windows \uACC4\uC815\uC744 \uD655\uC778\uD574 \uC8FC\uC138\uC694. \uC791\uC5C5 \uD30C\uC77C\uC740 \uADF8\uB300\uB85C \uBCF4\uC874\uB429\uB2C8\uB2E4.", STORE_CONFLICT: "\uB2E4\uB978 \uC388 \uC571\uC5D0\uC11C \uC778\uC99D \uC815\uBCF4\uB97C \uBCC0\uACBD\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694.", BRIDGE: "\uc388 \uc2dc\ub9ac\uc988 Windows \uc571\uc5d0\uc11c \ub2e4\uc2dc \uc2e4\ud589\ud574 \uc8fc\uc138\uc694.", CLOCK: "PC \uB0A0\uC9DC\uC640 \uC2DC\uAC04\uC774 \uC774\uC804\uBCF4\uB2E4 \uB4A4\uB85C \uBCC0\uACBD\uB410\uC2B5\uB2C8\uB2E4. \uB0A0\uC9DC\uB97C \uBC14\uB85C\uC7A1\uACE0 \uC628\uB77C\uC778\uC73C\uB85C \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694.", KEYS: "\uC11C\uBA85 \uD0A4 \uBAA9\uB85D\uC744 \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694." };
Object.assign(messages, { EDU_EXPIRED: "\uAD50\uC721\uC6A9 \uC774\uC6A9 \uAE30\uAC04\uC774 \uB05D\uB0AC\uC2B5\uB2C8\uB2E4. \uC774\uBA54\uC77C\uB85C \uC790\uACA9\uC744 \uB2E4\uC2DC \uC778\uC99D\uD574 \uC8FC\uC138\uC694.", EDU_SUSPENDED: "\uAD50\uC721\uC6A9 \uAD8C\uD55C\uC774 \uC815\uC9C0\uB410\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790\uC5D0\uAC8C \uBB38\uC758\uD574 \uC8FC\uC138\uC694.", REVERIFY_TOO_EARLY: "\uAD50\uC721\uC6A9 \uC790\uACA9 \uC7AC\uC778\uC99D\uC740 \uB9CC\uB8CC 30\uC77C \uC804\uBD80\uD130 \uAC00\uB2A5\uD569\uB2C8\uB2E4.", NOT_EDU: "\uAD50\uC721\uC6A9 \uC7AC\uC778\uC99D \uB300\uC0C1 \uACC4\uC815\uC774 \uC544\uB2D9\uB2C8\uB2E4.", CODE_INVALID: "\uC774\uC6A9\uAD8C \uCF54\uB4DC\uAC00 \uC62C\uBC14\uB974\uC9C0 \uC54A\uAC70\uB098 \uC0AC\uC6A9\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uBC1C\uAE09\uBC1B\uC740 \uC774\uBA54\uC77C \uACC4\uC815\uACFC \uCF54\uB4DC\uB97C \uD655\uC778\uD574 \uC8FC\uC138\uC694.", CODE_LOCKED: "\uC785\uB825 \uC2E4\uD328\uAC00 \uB9CE\uC544 \uC7A0\uC2DC \uB4F1\uB85D\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.", SUSPENDED: "\uD574\uB2F9 \uC774\uC6A9\uAD8C\uC774 \uC815\uC9C0\uB410\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790\uC5D0\uAC8C \uBB38\uC758\uD574 \uC8FC\uC138\uC694.", DEVICE_MISMATCH: "\uB85C\uADF8\uC778 \uACC4\uC815\uACFC PC \uB4F1\uB85D \uC815\uBCF4\uAC00 \uC77C\uCE58\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uB85C\uADF8\uC778\uD574 \uC8FC\uC138\uC694.", SIGNATURE_REQUIRED: "PC \uC778\uC99D\uC744 \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694." });
Object.assign(messages, { AUTH_RESPONSE_INVALID: "\uC774\uBA54\uC77C \uC778\uC99D \uC751\uB2F5 \uD615\uC2DD\uC774 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uC800\uC7A5\uACFC PC \uB4F1\uB85D\uC744 \uC911\uB2E8\uD588\uC2B5\uB2C8\uB2E4.", STORE_VERIFY_FAILED: "\uC800\uC7A5\uD55C \uC778\uC99D \uC815\uBCF4\uB97C \uB2E4\uC2DC \uC77D\uC5B4 \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. PC \uB4F1\uB85D\uC744 \uC911\uB2E8\uD588\uC2B5\uB2C8\uB2E4.", STORE_MISSING: "\uACF5\uD1B5 \uC778\uC99D \uC800\uC7A5\uC18C\uAC00 \uC5C6\uC5B4\uC84C\uC2B5\uB2C8\uB2E4. \uC790\uB3D9 \uC7AC\uC0DD\uC131 \uC5C6\uC774 \uC791\uC5C5\uC744 \uC911\uB2E8\uD588\uC2B5\uB2C8\uB2E4.", SESSION_MISSING: "\uACF5\uD1B5 \uC800\uC7A5\uC18C\uC5D0 \uB85C\uADF8\uC778 \uD1A0\uD070\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uB85C\uADF8\uC544\uC6C3 \uB610\uB294 \uC800\uC7A5 \uC2E4\uD328 \uC5EC\uBD80\uB97C \uD655\uC778\uD574 \uC8FC\uC138\uC694.", ACCOUNT_CHANGED: "\uACF5\uD1B5 \uACC4\uC815\uC774 \uBCC0\uACBD\uB410\uC2B5\uB2C8\uB2E4. \uD604\uC7AC \uACC4\uC815\uC744 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC9C4\uD589\uD574 \uC8FC\uC138\uC694.", SESSION_CHANGED: "\uACF5\uD1B5 \uB85C\uADF8\uC778 \uC815\uBCF4\uAC00 \uBCC0\uACBD\uB410\uC2B5\uB2C8\uB2E4. \uCD5C\uC2E0 \uC0C1\uD0DC\uB97C \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC9C4\uD589\uD574 \uC8FC\uC138\uC694.", IDENTITY_CHANGED: "\uACF5\uD1B5 PC \uC778\uC99D \uD0A4\uAC00 \uBCC0\uACBD\uB410\uC2B5\uB2C8\uB2E4. \uAE30\uC874 \uD0A4\uB97C \uB36E\uC5B4\uC4F0\uC9C0 \uC54A\uACE0 \uC911\uB2E8\uD588\uC2B5\uB2C8\uB2E4.", STORE_ERROR: "\uACF5\uD1B5 \uC778\uC99D \uC815\uBCF4\uB97C \uC800\uC7A5\uD558\uAC70\uB098 \uC77D\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. PC \uB4F1\uB85D\uC744 \uC911\uB2E8\uD588\uC2B5\uB2C8\uB2E4." });
function normalizeLicenseCode(raw) {
  let code = raw.toUpperCase().replace(/[\s-]/g, "");
  if (code.length === 16 && code.startsWith("SSEN")) code = code.slice(4);
  if (!/^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{12}$/.test(code)) throw Error("CODE_INVALID");
  return code;
}
function emailValue(raw) {
  const email = raw.trim().toLowerCase();
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw Error("BAD_EMAIL");
  return email;
}
var blocks = /* @__PURE__ */ new Set(["ACCOUNT_SUSPENDED", "LICENSE_REVOKED", "LICENSE_EXPIRED", "LICENSE_UNREGISTERED", "TRIAL_NOT_STARTED", "TRIAL_EXPIRED", "DEVICE_DEACTIVATED", "DEVICE_NOT_FOUND", "BAD_SIGNATURE", "EDU_EXPIRED", "EDU_SUSPENDED"]);
var AuthClient = class {
  constructor(bridge, app = "cut") {
    this.app = app;
    this.bridge = bridge;
  }
  state = null;
  revision = 0;
  sessionConfirmed = false;
  diagnostics = [];
  lastFailure = null;
  operation = "init";
  trace(stage, info = {}) {
    const item = { at: (/* @__PURE__ */ new Date()).toISOString(), operation: this.operation, stage };
    for (const k of ["source", "code", "traceId", "httpStatus", "revision", "tokenPresent", "accountPresent", "tokenSame", "accountSame", "spec", "outcome", "expiresAtSeconds", "nowSeconds", "serverTimeSeconds", "storeCause", "storeStage", "exitCode", "netCause", "netVia"]) if (info[k] !== void 0) item[k] = info[k];
    this.diagnostics.push(item);
    if (this.diagnostics.length > 60) this.diagnostics.shift();
    if (info.outcome === "failed") this.lastFailure = item;
  }
  async step(stage, fn) {
    try {
      return await fn();
    } catch (e) {
      e.stage ??= stage;
      e.source ??= "local";
      throw e;
    }
  }
  session() {
    return { accountId: this.state?.accountId, accountToken: this.state?.accountToken, deviceId: this.state?.deviceId, seed: this.state?.seed };
  }
  async confirmSession(expected) {
    await this.step("store.readback", () => this.load(false));
    const accountSame = this.state?.accountId === expected.accountId, tokenSame = this.state?.accountToken === expected.accountToken;
    this.trace("store.readback", { revision: this.revision, tokenPresent: !!this.state?.accountToken, accountSame, tokenSame });
    if (!this.state?.accountToken) throw Object.assign(Error("SESSION_MISSING"), { stage: "store.readback" });
    if (!accountSame) throw Object.assign(Error("ACCOUNT_CHANGED"), { stage: "store.readback" });
    if (!tokenSame) throw Object.assign(Error("SESSION_CHANGED"), { stage: "store.readback" });
    if (this.state.deviceId !== expected.deviceId || this.state.seed !== expected.seed) throw Object.assign(Error("IDENTITY_CHANGED"), { stage: "store.readback" });
    this.sessionConfirmed = true;
  }
  busy = false;
  error = "";
  status = null;
  bridge;
  onchange = () => {
  };
  lock = Promise.resolve();
  anchorWall = Date.now() / 1e3;
  anchorMono = performance.now();
  nextTry = 0;
  retry = 0;
  now() {
    return Math.floor(Math.max(Date.now() / 1e3, this.anchorWall + (performance.now() - this.anchorMono) / 1e3));
  }
  async load(create = this.state === null && this.revision === 0) {
    this.sessionConfirmed = false;
    const r = await this.step("store.read", () => this.bridge({ op: "read" }));
    if (!Number.isSafeInteger(r.revision) || r.revision < 0) throw Error("STORE_CORRUPT");
    this.revision = r.revision;
    this.state = r.state;
    if (this.state && (typeof this.state.deviceId !== "string" || !this.state.deviceId || this.state.deviceId.length > 200 || typeof this.state.seed !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(this.state.seed) || un64(this.state.seed).length !== 32)) throw Error("STORE_CORRUPT");
    if (!this.state) {
      if (!create) throw Error("STORE_MISSING");
      this.state = { deviceId: "ssen-" + crypto.randomUUID(), seed: b64(utils.randomPrivateKey()), cache: emptyCache(), lastTime: 0 };
      await this.save();
    }
    this.anchorWall = Math.max(Date.now() / 1e3, this.state.lastTime || 0);
    this.anchorMono = performance.now();
    this.sessionConfirmed = true;
    this.trace("store.read", { revision: this.revision, tokenPresent: !!this.state.accountToken, accountPresent: !!this.state.accountId, expiresAtSeconds: Number.isSafeInteger(this.state.accountExpiresAt) ? this.state.accountExpiresAt : void 0, nowSeconds: Math.floor(Date.now() / 1e3) });
  }
  async save() {
    const expectedRevision = this.revision, expected = this.session();
    try {
      const r = await this.step("store.write", () => this.bridge({ op: "write", revision: expectedRevision, state: this.state }));
      if (r.revision !== expectedRevision + 1) throw Object.assign(Error("STORE_VERIFY_FAILED"), { stage: "store.write" });
      this.revision = r.revision;
      this.trace("store.write", { revision: this.revision, outcome: "saved" });
    } catch (e) {
      this.sessionConfirmed = false;
      try {
        await this.load(false);
        this.trace("store.recovery", { revision: this.revision, tokenPresent: !!this.state?.accountToken, accountSame: this.state?.accountId === expected.accountId, tokenSame: this.state?.accountToken === expected.accountToken, outcome: !this.state?.accountToken ? "logged-out" : this.state.accountId !== expected.accountId ? "account-changed" : this.state.accountToken !== expected.accountToken ? "session-changed" : "unchanged" });
      } catch {
        this.state = null;
        this.trace("store.recovery", { outcome: "unreadable" });
      }
      throw e;
    }
  }
  async persistClock() {
    if (!this.state) return;
    this.state.lastTime = Math.max(this.state.lastTime || 0, this.now());
    const expected = this.session(), time = this.state.lastTime;
    await this.save();
    await this.load(false);
    if (Object.keys(expected).some((k) => this.state?.[k] !== expected[k]) || this.state.lastTime < time) throw Object.assign(Error("STORE_VERIFY_FAILED"), { stage: "clock.readback" });
    this.trace("clock.readback", { revision: this.revision, outcome: "verified" });
  }
  verdict() {
    if (!this.state) return "BRIDGE";
    if (Date.now() / 1e3 + 300 < (this.state.lastTime || 0)) return "CLOCK";
    if (this.state.block) return this.state.block;
    if (!this.state.token) return "LOGIN";
    try {
      return verifyLicense(this.state.token, this.state.cache, this.now(), { iss: ISS, sub: this.state.accountId, regId: this.state.regId, deviceId: this.state.deviceId, app: this.app });
    } catch {
      return "CLAIMS";
    }
  }
  canEdit() {
    return ["OK", "OFFLINE_GRACE"].includes(this.verdict());
  }
  async run(fn) {
    if (this.busy) throw Error("BUSY");
    this.busy = true;
    this.onchange();
    const go = async () => {
      try {
        await this.load();
        const result = await fn();
        this.error = "";
        return result;
      } catch (e) {
        this.error = e.message;
        const code = /^[A-Z][A-Z0-9_]{0,70}$/.test(e.message) ? e.message : "INTERNAL_ERROR";
        this.trace(e.stage || "operation", { source: e.source || "local", code, storeCause: e.storeCause, storeStage: e.storeStage, exitCode: e.exitCode, netCause: e.netCause, netVia: e.netVia, httpStatus: e.status, traceId: e.traceId, spec: e.spec, revision: this.revision, tokenPresent: !!this.state?.accountToken, outcome: "failed" });
        throw e;
      } finally {
        this.busy = false;
        this.onchange();
      }
    };
    this.lock = this.lock.catch(() => {
    }).then(go);
    return this.lock;
  }
  async api(path, body = {}, headers = {}, method = "POST") {
    const r = await this.step(path, () => this.bridge({ op: "api", path, method, headers, body: method === "GET" ? "" : typeof body === "string" ? body : JSON.stringify(body) }));
    const safe = (v) => typeof v === "string" && /^[A-Za-z0-9_.:-]{1,100}$/.test(v) ? v : void 0;
    this.trace(path, { source: "server", httpStatus: r.status, spec: safe(r.spec), serverTimeSeconds: r.serverTime, outcome: r.status >= 200 && r.status < 300 ? "ok" : "rejected" });
    let data;
    try {
      data = JSON.parse(r.body);
    } catch {
      throw Object.assign(Error("AUTH_RESPONSE_INVALID"), { stage: path, source: "server", status: r.status });
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) throw Object.assign(Error("AUTH_RESPONSE_INVALID"), { stage: path, source: "server", status: r.status });
    if (r.status < 200 || r.status >= 300) {
      const code = data.error?.code || "NETWORK";
      if (this.state && blocks.has(code) && ["/status", "/license/token", "/trial/start", "/license/redeem", "/edu/reverify", "/edu/reverify/send", "/devices/register", "/devices/deactivate"].includes(path)) {
        this.state.block = code;
        this.state.token = null;
        this.state.claims = null;
        await this.save();
      }
      const e = Error(code);
      e.status = r.status;
      e.stage = path;
      e.source = "server";
      e.traceId = safe(data.error?.traceId);
      e.spec = safe(r.spec);
      e.retryAt = data.error?.retryAt;
      throw e;
    }
    return { data, serverTime: r.serverTime };
  }
  async signed(path, body, register = false, withBearer = false) {
    const session = this.session();
    if ((register || withBearer) && !session.accountToken) throw Object.assign(Error("SESSION_MISSING"), { stage: path });
    for (let n = 0; n < 2; n++) {
      const { data } = await this.api("/challenge");
      const raw = JSON.stringify(body), reg = register ? null : this.state.regId, bearer = register || withBearer ? session.accountToken : null;
      const canonical = canonicalV3("POST", "/api/public/v1" + path, data.nonce, reg, bearer, raw);
      const headers = { "X-Ssen-Nonce": data.nonce, "X-Ssen-Signature": b64(sign(enc2.encode(canonical), un64(session.seed))) };
      if (reg) headers["X-Ssen-Reg"] = reg;
      if (bearer) headers.Authorization = "Bearer " + bearer;
      try {
        return await this.api(path, raw, headers);
      } catch (e) {
        if (e.message === "NONCE_INVALID" && n === 0) continue;
        throw e;
      }
    }
    throw Error("NONCE_INVALID");
  }
  async send(raw) {
    const email = emailValue(raw);
    return this.run(() => this.api("/auth/otp/send", { email }));
  }
  async login(raw, code) {
    const email = emailValue(raw);
    if (!/^\d{6}$/.test(code)) throw Error("OTP_WRONG");
    return this.run(async () => {
      const { data } = await this.api("/auth/otp/verify", { email, code });
      if (typeof data.accountToken !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(data.accountToken) || typeof data.accountId !== "string" || !data.accountId || !Number.isSafeInteger(data.expiresAt) || data.expiresAt <= 0 || data.expiresAt >= 1e11) throw Object.assign(Error("AUTH_RESPONSE_INVALID"), { stage: "/auth/otp/verify", source: "local" });
      const sameAccount = this.state.accountId === data.accountId;
      this.status = null;
      this.sessionConfirmed = false;
      this.state = { ...this.state, email, accountId: data.accountId, accountToken: data.accountToken, accountExpiresAt: data.expiresAt, regId: sameAccount ? this.state.regId : null, token: sameAccount ? this.state.token : null, claims: sameAccount ? this.state.claims : null, block: sameAccount ? this.state.block : null, edu: data.edu || null, redeemRetryAt: 0 };
      const expected = this.session();
      await this.save();
      await this.confirmSession(expected);
      await this.fetchStatus();
      await this.confirmSession(expected);
      await this.register();
      await this.refreshInner();
    });
  }
  async fetchStatus() {
    const { data } = await this.api("/status", {}, { Authorization: "Bearer " + this.state.accountToken }, "GET");
    this.status = data;
    this.state.edu = data.edu || null;
    await this.save();
    return data;
  }
  async register() {
    const { data } = await this.signed("/devices/register", { deviceId: this.state.deviceId, publicKey: b64(getPublicKey(un64(this.state.seed))), app: "ssen-" + this.app, os: "Windows" }, true);
    if (typeof data.regId !== "string" || !data.regId) throw Object.assign(Error("AUTH_RESPONSE_INVALID"), { stage: "/devices/register" });
    this.state.regId = data.regId;
    this.state.block = null;
    const expected = this.session();
    await this.save();
    await this.confirmSession(expected);
    if (this.state.regId !== data.regId) throw Object.assign(Error("STORE_VERIFY_FAILED"), { stage: "register.readback" });
  }
  async registerAgain() {
    const expected = this.session();
    return this.run(async () => {
      await this.confirmSession(expected.accountToken ? expected : this.session());
      await this.register();
      await this.refreshInner();
    });
  }
  async startTrial() {
    return this.run(async () => {
      if (!this.state.regId) await this.register();
      await this.signed("/trial/start", {});
      await this.refreshInner();
    });
  }
  async refresh() {
    return this.run(() => this.refreshInner());
  }
  async refreshInner() {
    try {
      const { data: keyData, serverTime } = await this.api("/keys", {}, {}, "GET");
      const checkTime = serverTime || this.now();
      const accepted = acceptKeyList(keyData.keyList, TRUST, checkTime, this.state.cache || emptyCache());
      if (!accepted.ok) throw Error("KEYS");
      this.state.cache = accepted.cache;
      await this.save();
      if (!this.state.regId) {
        if (this.state.accountToken) await this.fetchStatus();
        return;
      }
      const { data } = await this.signed("/license/token", { app: "ssen-" + this.app });
      const expected = { iss: ISS, sub: this.state.accountId, regId: this.state.regId, deviceId: this.state.deviceId, app: this.app };
      const result = verifyLicense(data.token, this.state.cache, checkTime, expected);
      if (!["OK", "OFFLINE_GRACE", "EXPIRED", "ENT_EXPIRED"].includes(result)) throw Error("TOKEN_" + result);
      const claims = JSON.parse(new TextDecoder().decode(un64(data.token.split(".")[1])));
      this.state.token = data.token;
      this.state.claims = claims;
      this.state.block = null;
      this.state.lastTime = checkTime;
      this.anchorWall = checkTime;
      this.anchorMono = performance.now();
      await this.save();
      this.retry = 0;
      this.nextTry = Date.now() + Math.max(6e4, (claims.refresh_at - checkTime) * 1e3);
      if (this.state.accountToken) {
        try {
          await this.fetchStatus();
        } catch {
        }
      }
    } catch (e) {
      if (blocks.has(e.message)) {
        this.state.block = e.message;
        this.state.token = null;
        this.state.claims = null;
        await this.save();
      }
      this.retry++;
      this.nextTry = Date.now() + Math.min(6e4, 1e3 * 2 ** Math.min(this.retry, 6));
      throw e;
    }
  }
  async syncEntitlement() {
    try {
      await this.fetchStatus();
      await this.refreshInner();
      return null;
    } catch (e) {
      this.error = e.message;
      return e.message;
    }
  }
  async redeem(raw) {
    const code = normalizeLicenseCode(raw);
    return this.run(async () => {
      if (!this.state.accountToken) throw Error("UNAUTHORIZED");
      if (!this.state.regId) throw Error("DEVICE_NOT_FOUND");
      if (Date.now() / 1e3 < (this.state.redeemRetryAt || 0)) {
        const e = Error("CODE_LOCKED");
        e.retryAt = this.state.redeemRetryAt;
        throw e;
      }
      let data;
      try {
        ({ data } = await this.signed("/license/redeem", { code }, false, true));
      } catch (e) {
        if (e.message === "CODE_LOCKED" && Number.isSafeInteger(e.retryAt)) {
          this.state.redeemRetryAt = e.retryAt;
          await this.save();
        }
        throw e;
      }
      return { ...data, syncError: await this.syncEntitlement() };
    });
  }
  async sendEdu() {
    return this.run(async () => {
      if (!this.state.accountToken) throw Error("UNAUTHORIZED");
      return this.api("/edu/reverify/send", {}, { Authorization: "Bearer " + this.state.accountToken });
    });
  }
  async reverifyEdu(code) {
    if (!/^\d{6}$/.test(code)) throw Error("OTP_WRONG");
    return this.run(async () => {
      if (!this.state.accountToken) throw Error("UNAUTHORIZED");
      const { data } = await this.api("/edu/reverify", { code }, { Authorization: "Bearer " + this.state.accountToken });
      this.state.edu = data.edu;
      await this.save();
      return { ...data, syncError: await this.syncEntitlement() };
    });
  }
  async devices() {
    return this.run(() => this.fetchStatus());
  }
  async deactivate(regId) {
    return this.run(async () => {
      await this.api("/devices/deactivate", { regId }, { Authorization: "Bearer " + this.state.accountToken });
      if (regId === this.state.regId) {
        this.state.token = null;
        this.state.regId = null;
        this.state.block = "DEVICE_DEACTIVATED";
        await this.save();
      }
      await this.fetchStatus();
    });
  }
  async logout() {
    return this.run(async () => {
      this.state = { ...this.state };
      for (const key of ["email", "accountId", "accountToken", "accountExpiresAt", "regId", "token", "claims", "block", "edu", "redeemRetryAt"]) delete this.state[key];
      this.status = null;
      await this.save();
    });
  }
  async tick() {
    if (this.busy) return;
    try {
      await this.run(async () => {
        await this.persistClock();
        if (this.state.regId && Date.now() >= this.nextTry) await this.refreshInner();
      });
    } catch (e) {
      throw e;
    }
  }
};

// service.ts
function createAuthService(bridge, app = "pdf") {
  // ssen-auth-kit: 앱 짧은 이름(cut·pdf·img·clean·doc·player 등). 서버 /devices/register·/license/token에 "ssen-" + app으로 가고, 토큰 scope에 이 이름이 있어야 편집 가능.
  if (typeof app !== "string" || !/^[a-z][a-z0-9]{1,15}$/.test(app)) throw Error("BAD_APP_ID");
  const client = new AuthClient(bridge, app);
  let failure = "";
  let ready = false;
  let activeError = null;
  function summary() {
    const verdict = failure || client.verdict(), valid = ["OK", "OFFLINE_GRACE", "EXPIRED", "ENT_EXPIRED"].includes(verdict);
    let c = null;
    if (valid && client.state?.token) {
      try {
        c = JSON.parse(Buffer.from(client.state.token.split(".")[1], "base64url").toString("utf8"));
      } catch {
      }
    }
    const s = client.state || {};
    return { activeError, accountPresent: !!s.accountId, hasLicense: !!c && !s.block, diagnostics: client.diagnostics, lastFailure: client.lastFailure, ready, verdict, canEdit: !failure && !/^STORE_/.test(activeError?.code || "") && client.canEdit(), email: s.email || "", loggedIn: client.sessionConfirmed && !!s.accountToken, registered: !!s.regId, plan: c?.plan || null, expiresAt: c?.ent_exp ?? null, unlimited: c?.plan === "licensed" && c.ent_exp === null, edu: s.edu || null, retryAt: s.redeemRetryAt || 0, message: messages[failure || client.error || verdict] || { "LOGIN": "\uC774\uBA54\uC77C\uB85C \uB85C\uADF8\uC778\uD574 \uC8FC\uC138\uC694.", "EXPIRED": "\uC624\uD504\uB77C\uC778 \uD5C8\uAC00\uC99D\uC774 \uB9CC\uB8CC\uB410\uC2B5\uB2C8\uB2E4. \uC628\uB77C\uC778\uC73C\uB85C \uD655\uC778\uD574 \uC8FC\uC138\uC694.", "ENT_EXPIRED": "\uC774\uC6A9 \uAE30\uAC04\uC774 \uB05D\uB0AC\uC2B5\uB2C8\uB2E4.", "OFFLINE_GRACE": "\uC778\uD130\uB137\uC5D0 \uC5F0\uACB0\uD574 \uC774\uC6A9\uAD8C\uC744 \uAC31\uC2E0\uD574 \uC8FC\uC138\uC694." }[verdict] || "", devices: client.status?.devices?.map((d) => ({ regId: d.regId, os: d.os, registeredAt: d.registeredAt, apps: d.apps, current: d.regId === s.regId })) || [], devicesUsed: client.status?.devicesUsed, maxDevices: client.status?.maxDevices };
  }
  async function act(action, args = {}) {
    let result = null;
    const started = (/* @__PURE__ */ new Date()).toISOString();
    try {
      client.operation = action;
      failure = "";
      switch (action) {
        case "peek":
          await client.load();
          ready = true;
          break;
        case "init":
        case "sync":
          // 1.0.2: 이미 읽은 상태가 있고 등록된 PC면 tick 안(run)에서 다시 읽으므로 앞의 읽기는 건너뜀(PowerShell 1번 절약)
          if (!(client.state && client.state.regId)) await client.load();
          ready = true;
          if (client.state.regId) await client.tick();
          break;
        case "send":
          result = await client.send(args.email);
          break;
        case "login":
          await client.login(args.email, args.code);
          break;
        case "trial":
          await client.startTrial();
          break;
        case "refresh":
          await client.refresh();
          break;
        case "register":
          await client.registerAgain();
          break;
        case "redeem":
          result = await client.redeem(args.code);
          break;
        case "eduSend":
          result = await client.sendEdu();
          break;
        case "eduVerify":
          result = await client.reverifyEdu(args.code);
          break;
        case "devices":
          await client.devices();
          break;
        case "deactivate":
          await client.deactivate(args.regId);
          break;
        case "logout":
          await client.logout();
          break;
        default:
          throw Error("BAD_OPERATION");
      }
      const verified = client.diagnostics.some((d) => (d.stage === "clock.readback" && d.outcome === "verified" || d.stage === "store.readback" && d.accountSame && d.tokenSame) && d.operation === action && d.at >= started);
      if (verified || !activeError || !/^STORE_/.test(activeError.code) && !["init", "sync", "peek"].includes(action)) {
        activeError = null;
        client.error = "";
      }
      return { ok: true, already: result?.already || false, state: summary(), syncError: result?.syncError || null };
    } catch (e) {
      if (/^STORE_|^BRIDGE/.test(e.message)) failure = e.message;
      const code = /^[A-Z][A-Z0-9_]{0,70}$/.test(e.message) ? e.message : "INTERNAL_ERROR";
      client.error = code;
      if (client.lastFailure?.operation !== action || client.lastFailure?.code !== code) client.trace(e.stage || "operation", { code, storeCause: e.storeCause, storeStage: e.storeStage, exitCode: e.exitCode, netCause: e.netCause, netVia: e.netVia, source: e.source || "local", httpStatus: e.status, traceId: e.traceId, revision: client.revision, tokenPresent: !!client.state?.accountToken, outcome: "failed" });
      const message = /^STORE_/.test(code) && ["init", "sync", "peek"].includes(action) ? "\uACF5\uD1B5 \uC778\uC99D \uC0C1\uD0DC\uB97C \uAC31\uC2E0\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAE30\uC874 \uC791\uC5C5\uC740 \uBCF4\uC874\uB429\uB2C8\uB2E4." : messages[code] || "\uC778\uC99D\uC744 \uC644\uB8CC\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694.";
      activeError = { code, message, operation: action, stage: e.stage || "operation" };
      return { ok: false, error: code, message, state: summary() };
    }
  }
  async function authorize() {
    try {
      await client.load();
      failure = "";
      if (!summary().canEdit) throw Error("AUTH_REQUIRED");
      return true;
    } catch (e) {
      throw Error("\uC774\uC6A9\uAD8C \uD655\uC778\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uC791\uC5C5 \uD30C\uC77C \uC800\uC7A5\uC740 \uACC4\uC18D \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.");
    }
  }
  return { act, summary, authorize };
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  createAuthService
});
/*! Bundled license information:

@noble/ed25519/index.js:
  (*! noble-ed25519 - MIT License (c) 2019 Paul Miller (paulmillr.com) *)

@noble/hashes/esm/utils.js:
  (*! noble-hashes - MIT License (c) 2022 Paul Miller (paulmillr.com) *)
*/
