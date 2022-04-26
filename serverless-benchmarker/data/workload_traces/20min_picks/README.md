# Pattern Selection

Selection of archetypical invocation patterns from the Azure Functions Dataset.

## List

* spikes: `invocations043-time2-count.pdf`
  * 4 spikes from zero base load to ~5rps or 3 after the 3min warmup
* jump: `invocations034-time1-count.pdf`
  * 1 jump right to 4.6 r/sec after the 3min warmup, then going back to 2.5 r/sec
* fluctuation (bursty): `invocations009-time1-count.pdf`
  * classic ups and downs around 15 r/sec baseline
* steady (constant): `invocations007-time1-count.pdf`
  * baseline of 5.6 r/sec with minimal changes

## R Export Config

```r
# 2022-01-06 Select higher rps for constant + bursty
# 043-time2 ~340 ipm / 5.6 ips
constant <- '2c5d363481a100391a50d5397fece786de8d4b86fc02c8880a78bcfa7b297139'
# 009-time1 ~900 ipm / 15 ips
bursty <- '08f7ff6d9380a3c0442130789c39c3006b6648ba613a3cc9f34de200ae2ee057'
# 034-time1 base 0 ipm, spikes to 300 ipm / 5 rps
spikes <- '02783877a12468a4fcb9140ed732dd443dac2722ebf8d4a1965dc9e0f04c13e1'
# 007-time1 ~280 ipm / 4.5 r/sec peak, ~150 ipm / 2.5 rps base
jump <- '0d82a08ef7b0ee97684b504d8ecc22308d43a299d8bd823eb38e55b2b4830cf1'

# ...

# Variants
constant.file <- paste(baseDir, "/constant.csv", sep = '')
export_trace(constant, constant.file, time2, minutes)

bursty.file <- paste(baseDir, "/bursty.csv", sep = '')
export_trace(bursty, bursty.file, time1, minutes)

spikes.file <- paste(baseDir, "/spikes.csv", sep = '')
export_trace(spikes, spikes.file, time1, minutes)

jump.file <- paste(baseDir, "/jump.csv", sep = '')
export_trace(jump, jump.file, time1, minutes)
```
