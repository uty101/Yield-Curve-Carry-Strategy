## What carry does not tell you

Nine things this book's numbers do not say, each with the figure from this
repo that bounds it.

**1. The return is carry net of a losing yield bet, and the yield bet is the
larger number.** Over the full window the headline book earned
75.68% of carry, gave back 53.43% to yield changes
and 5.13% to costs, and kept 17.13%. A reader who sees
only the net figure will under-estimate both the gross carry and the size of
the directional risk that offset it. The losing decades are
1990s, 2020s: decades where the yield move was larger than the carry,
not decades where the carry stopped.

**2. 2022 is what that looks like in one year.** The book lost
4.41% over 12 months, of which carry earned
3.69% and yield changes cost 7.84%. Carry was
positive in 12 of those months, including the worst
one (2022-02-28, a loss of 1.70%). Duration
neutrality did not protect the book, because the long leg sat where the curve
moved most;
a book neutral in duration is not neutral in *where on the curve* the duration
sits.

**3. The slope overlay is flat gross and loses its costs.** Over
29 years and 181 in-sample trades it made
-190 bp gross, paid 722 bp in costs and returned
-912 bp. The 5 worst trades alone cost
684 bp: GB 2008-09 flattener -176 bp; FR 2022-08 steepener -150 bp; CA 2008-09 flattener -134 bp; CA 2021-01 flattener -114 bp; JP 1998-11 flattener -110 bp. They share a shape — a
mean-reversion slope signal is short the trend, so it fades a curve move that
keeps going, and it does that hardest in the months the move is largest. An
overlay that is flat before costs is not a diversifier; it is a fee.

**4. Duration neutrality is not currency neutrality.** The book is neutral in
duration and not in notional, and notional is what carries currency risk. The
unhedged book's monthly return regresses on its own currency-weighted FX term
with an R-squared of 95.3% and a beta of 0.96: almost all of
what the unhedged run earned or lost is the exchange rate, not the curve. Its
mean absolute net foreign notional is 1.86 units of capital
and its maximum 3.39. Every unhedged number in this report
is a currency bet with a carry book attached.

**5. The funding rate is a policy rate used as a three-month anchor.** The
financing leg of every excess return is the central bank's policy rate, not a
rate anyone can borrow at for three months. Where the policy series has gaps
they are filled from the OECD immediate rate: 116 months in
total, all in JP (JP 1999-03-31 to 2000-07-31 (17 months); JP 2001-04-30 to 2006-02-28 (59 months); JP 2013-05-31 to 2016-08-31 (40 months)). The logged
robustness run on the OECD three-month interbank rate returns
0.64% a year at a Sharpe of 0.284 against
the headline's 0.59% and 0.265 — close
enough that the choice does not carry the result, but the interbank series
prices bank credit, and in 2008 that credit spread would read here as carry.

**6. The cross-currency basis is not measured.** The hedged return is
the local excess return by covered interest parity, and covered interest
parity has not held since 2008. No free basis series was found
(`decisions/basis.md` records the probe), so the error is not estimated; from
the brief it runs 20 to 50 bp in stress periods for the major pairs,
one-directional rather than noise, and wider at quarter and year ends. Every
hedged number here is a CIP-implied hedged number.

**7. The Nelson-Siegel lambda is unidentified on flat curves.** As lambda goes
to zero the slope loading becomes the level loading and the design matrix goes
collinear, so the fit runs to the edge of the grid and stops there. On the
free-lambda fits that happens in 34.6% of
CA months (31.6% of them at the lower
bound) and as little as 4.6% of FR
months. Where lambda is on a bound the reported betas are coefficients on a
nearly singular basis and should not be read as level, slope and curvature.
Nothing in the strategy reads them — the signal is built from zero yields —
but the fitted-curve charts inherit the problem.

**8. The US curve is built from on-the-run yields, which are rich.** Against
the Fed's own GSW fitted curve the CMT par yield at 10 years
differs by -7.9 bp on average and -7.2 bp at the median over
661 months — the CMT yield is the lower, which is the on-the-run
bond being the dearer. That is the on-the-run premium, and it is a level
shift on one country's curve that no other country in this book carries. It
enters the carry signal as a small standing tilt away from the US, not as
noise.

**9. Buckets enter and leave mid-sample, and the universe is not the same book
throughout.** Inside the strategy window 131 bucket-months
enter and 169 leave, across CA, DE, FR, GB, JP, US. A
cross-sectional rank is taken over whatever is available that month, so the
same signal value means a different thing in a month with four countries and a
month with six. The two sample windows exist for exactly this reason and every
result is reported on both.

**And one measurement note.** The duration-convexity approximation of the
monthly return, which the brief asks for, is diagnostic here and never inside
any identity. Its mean error runs -0.69 bp to -0.41 bp by
tenor, with a worst single bucket-month of 42 bp at
20 years. Every return in this report is a full
repricing.

**What the robustness rows changed.** Country-scope neutrality instead of
book-wide takes the headline to 0.19% a year at
0.120; excluding the GB 30-year, 0.63% at
0.280; zero costs, 0.77% at 0.344;
double costs, 0.41% at 0.185. Costs move the
result more than any modelling choice in the list, and the country-scope run
moves it most of all — which is the honest reading that book-wide neutrality
is doing real work and is a choice, not a detail.
