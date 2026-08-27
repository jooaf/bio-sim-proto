//! Self-deterministic RNG for the Rust kernel.
//!
//! The kernel does NOT reproduce Python's Mersenne Twister streams; it has its
//! own xoshiro256++ generator, validated by conservation and same-seed
//! determinism instead of bitwise parity.

#[derive(Clone, Debug)]
pub struct Rng {
    s: [u64; 4],
}

#[inline]
fn splitmix(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
    let mut z = *state;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

impl Rng {
    pub fn new(seed: u64) -> Self {
        let mut st = seed;
        Rng {
            s: [
                splitmix(&mut st),
                splitmix(&mut st),
                splitmix(&mut st),
                splitmix(&mut st),
            ],
        }
    }

    #[inline]
    pub fn next_u64(&mut self) -> u64 {
        let result = self.s[0]
            .wrapping_add(self.s[3])
            .rotate_left(23)
            .wrapping_add(self.s[0]);
        let t = self.s[1] << 17;
        self.s[2] ^= self.s[0];
        self.s[3] ^= self.s[1];
        self.s[1] ^= self.s[2];
        self.s[0] ^= self.s[3];
        self.s[2] ^= t;
        self.s[3] = self.s[3].rotate_left(45);
        result
    }

    /// Uniform float in [0, 1) with 53 bits of resolution (Python `random()` analogue).
    #[inline]
    pub fn f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / ((1u64 << 53) as f64))
    }

    #[inline]
    pub fn uniform(&mut self, a: f64, b: f64) -> f64 {
        a + (b - a) * self.f64()
    }

    /// Standard normal via Box-Muller (kernel is self-deterministic).
    #[inline]
    pub fn gauss(&mut self) -> f64 {
        let u1 = 1.0 - self.f64(); // in (0, 1], avoids ln(0)
        let u2 = self.f64();
        (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
    }

    /// Uniform index in [0, n), using rejection to avoid modulo bias.
    #[inline]
    pub fn below(&mut self, n: u64) -> u64 {
        assert!(n > 0, "random range must be non-empty");
        let threshold = n.wrapping_neg() % n;
        loop {
            let value = self.next_u64();
            if value >= threshold {
                return value % n;
            }
        }
    }

    /// Inclusive integer range, Python `randint(a, b)`.
    #[inline]
    pub fn randint(&mut self, a: i64, b: i64) -> i64 {
        a + self.below((b - a + 1) as u64) as i64
    }

    /// Python `random() < p` idiom.
    #[inline]
    pub fn chance(&mut self, p: f64) -> bool {
        self.f64() < p
    }

    pub fn hash_into(&self, h: &mut Fnv) {
        for value in self.s {
            h.u64(value);
        }
    }

    /// Fisher-Yates shuffle.
    pub fn shuffle<T>(&mut self, v: &mut [T]) {
        for i in (1..v.len()).rev() {
            let j = self.below((i + 1) as u64) as usize;
            v.swap(i, j);
        }
    }

    /// k distinct indices out of n (partial Fisher-Yates; returned in random order).
    pub fn sample_indices(&mut self, n: usize, k: usize) -> Vec<usize> {
        let mut idx: Vec<usize> = (0..n).collect();
        let k = k.min(n);
        for i in 0..k {
            let j = i + self.below((n - i) as u64) as usize;
            idx.swap(i, j);
        }
        idx.truncate(k);
        idx
    }
}

/// splitmix64 finalizer used for per-chunk terrain seeds (mirrors world._mix64).
pub fn mix64(value: u64) -> u64 {
    let mut z = value.wrapping_add(0x9E37_79B9_7F4A_7C15);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

/// Deterministic FNV-1a 64-bit digest helper used for state digests.
pub struct Fnv(u64);

impl Fnv {
    pub fn new() -> Self {
        Fnv(0xcbf2_9ce4_8422_2325)
    }
    #[inline]
    pub fn u64(&mut self, v: u64) {
        for b in v.to_le_bytes() {
            self.0 ^= b as u64;
            self.0 = self.0.wrapping_mul(0x0000_0100_0000_01B3);
        }
    }
    #[inline]
    pub fn i64(&mut self, v: i64) {
        self.u64(v as u64);
    }
    #[inline]
    pub fn f64(&mut self, v: f64) {
        self.u64(v.to_bits());
    }
    #[inline]
    pub fn bytes(&mut self, v: &[u8]) {
        for &b in v {
            self.0 ^= b as u64;
            self.0 = self.0.wrapping_mul(0x0000_0100_0000_01B3);
        }
    }
    pub fn finish(&self) -> u64 {
        self.0
    }
}

impl Default for Fnv {
    fn default() -> Self {
        Self::new()
    }
}

/// Python `round()` semantics: round-half-to-even on an f64, returned as i64.
#[inline]
pub fn py_round(x: f64) -> i64 {
    let floor = x.floor();
    let d = x - floor;
    if d > 0.5 {
        floor as i64 + 1
    } else if d < 0.5 {
        floor as i64
    } else {
        // exactly .5: to even
        let f = floor as i64;
        if f % 2 == 0 {
            f
        } else {
            f + 1
        }
    }
}

/// statistics.median: true median (average of two middle values for even n).
pub fn median(values: &mut [f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    values.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = values.len();
    if n % 2 == 1 {
        values[n / 2]
    } else {
        (values[n / 2 - 1] + values[n / 2]) / 2.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rng_deterministic() {
        let mut a = Rng::new(42);
        let mut b = Rng::new(42);
        for _ in 0..1000 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
    }

    #[test]
    fn bounded_and_continuous_draws_are_balanced() {
        const SAMPLES: usize = 200_000;
        let mut bounded_rng = Rng::new(9);
        let mut buckets = [0usize; 7];
        for _ in 0..SAMPLES {
            buckets[bounded_rng.below(buckets.len() as u64) as usize] += 1;
        }
        let expected = SAMPLES as f64 / buckets.len() as f64;
        for count in buckets {
            assert!((count as f64 - expected).abs() / expected < 0.02);
        }

        let mut moment_rng = Rng::new(19);
        let mut uniform_sum = 0.0;
        let mut gaussian_sum = 0.0;
        let mut gaussian_square_sum = 0.0;
        for _ in 0..SAMPLES {
            uniform_sum += moment_rng.uniform(0.0, 1.0);
            let gaussian = moment_rng.gauss();
            gaussian_sum += gaussian;
            gaussian_square_sum += gaussian * gaussian;
        }
        let uniform_mean = uniform_sum / SAMPLES as f64;
        let gaussian_mean = gaussian_sum / SAMPLES as f64;
        let gaussian_variance = gaussian_square_sum / SAMPLES as f64 - gaussian_mean.powi(2);
        assert!((uniform_mean - 0.5).abs() < 0.005);
        assert!(gaussian_mean.abs() < 0.01);
        assert!((gaussian_variance - 1.0).abs() < 0.02);
    }

    #[test]
    fn py_round_half_even() {
        assert_eq!(py_round(0.5), 0);
        assert_eq!(py_round(1.5), 2);
        assert_eq!(py_round(2.5), 2);
        assert_eq!(py_round(-0.5), 0); // Python round(-0.5) == 0 (half-to-even)
        assert_eq!(py_round(-1.5), -2);
        assert_eq!(py_round(2.4), 2);
        assert_eq!(py_round(2.6), 3);
    }
}
