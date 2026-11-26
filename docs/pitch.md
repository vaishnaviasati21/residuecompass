# Residue Compass – Story, Pitch & Demo Runbook

**Team:** CODESTRIX (Vaishnavi Asati, Somya Asati, Akshara Khandelwal, Puneet Agarwal, Devansh Chaubey)  
**Event:** IIT Indore | MFSS SUSTAIN-AI 2026  

---

## 1. Problem Statement
After the kharif rice harvest, farmers in Punjab and Haryana have only **10 to 20 days** to clear paddy straw before sowing wheat. Clearing straw costs labour, machinery, and time—so many farmers burn it, causing severe seasonal air pollution and wasting a valuable biomass resource.

Despite Punjab distributing **~1.57 lakh straw-management machines** since 2018–19, burning persists because **information is missing**:
1. **When and where** will straw be ready?
2. **Does selling it actually pay** after baling and transport costs?
3. **Where is burning happening**, and with what confidence?

---

## 2. Why Now
- **Demand exists, coordination doesn't:** Power plants, pellet units, and biogas plants are scaling up (e.g., 3.12 lakh tonnes of straw pellets co-fired till Sept vs. the 2025–26 target of 11.83 lakh tonnes), creating real buyer demand if supply can be scheduled reliably.
- **Free, high-frequency Earth observation:** Sentinel-2 (10 m every ~5 days), NASA FIRMS (~375 m active fire points), and ERA5/IMD weather are all free and operational.
- **Last-mile reach:** Automated multilingual SMS/WhatsApp alerts let farmers receive clear pickup dates and ₹/tonne payouts without needing to navigate complex dashboards.

---

## 3. Pitch Script (~3 Minutes)

> **Hook (0:00–0:30):**  
> "Every October, farmers in Punjab and Haryana have just 10 to 20 days between harvesting paddy and sowing wheat. Punjab has already distributed over 1.57 lakh machines—yet stubble burning returns every year. Why? Because machines without timing and economics are blind. Nobody tells a farmer *when* their village's straw is ready, *whether* selling it beats burning or mulching, or *who* will pick it up."
>
> **Solution (0:30–1:15):**  
> "Meet **Residue Compass**—a Predict, Decide, and Verify platform.  
> First, we **Predict**: using Sentinel-2 NDVI curves and weather, we forecast village-level harvest dates and straw tonnage with a Low/Medium/High confidence tag.  
> Second, we **Decide**: we compare keeping straw, selling it, or using it as feed, and show the exact break-even price including fertilizer value, baling, and transport distance.  
> Third, we **Match & Notify**: we pair ready villages with nearby pellet or biogas buyers, balers, and trucks, and send the farmer a simple Punjabi or Hindi message: *'Your straw will be collected on Oct 24. You will get ₹1,500 per tonne.'*  
> Finally, we **Verify**: we combine NASA FIRMS fire points with Sentinel-2 burn scars to flag real burning with a confidence tag."
>
> **Live Demo (1:15–2:30):**  
> *(Walk through the 5-step demo order below on the live URL.)*
>
> **Close (2:30–3:00):**  
> "We don't claim unverified accuracy numbers—we test on unseen seasons, label every estimate as an assumption, and ship with a one-click demo mode so field officers and buyers can coordinate reliably even in low-connectivity districts. Residue Compass turns a 15-day crisis into a scheduled, profitable supply chain."

---

## 4. Exact Demo Order (One-Click Loop)
Endpoint: `POST /api/v1/demo/run?village_id=PB-SNG-0142`

1. **Predict (Forecast):** Show village `PB-SNG-0142` (Sangrur) — expected harvest `2026-10-20`, `410.0 t` straw, `MEDIUM` confidence with explicit reasons (`38% cloud cover in last 2 weeks`).
2. **Decide (Economics):** Show `best_option: "sell"`, break-even `₹1,180/t`, and live what-if simulation (`POST /api/v1/decisions/simulate`) if transport distance changes.
3. **Match:** Show `PROPOSED` match `M-20261012-0007` — `Sample Pellet Unit` (`38 km` away), baler `BAL-031`, truck `TRK-114`, pickup `2026-10-24` at `₹1,500/t` (`₹131,200` net to farmers).
4. **Notify:** Show the generated Punjabi (`pa`) message logged in `/api/v1/notifications`.
5. **Verify (Burn Check):** Show burn event `BE-20261023-0451` (`HIGH` confidence: 2 FIRMS fire points + Sentinel-2 burn scar of `3.1 ha`).

---

## 5. Rehearsal & Backup Checklist
- [ ] Rehearsal 1 completed (timed ≤ 3:00, live URL)
- [ ] Rehearsal 2 completed (with Q&A on confidence tags & assumptions)
- [ ] Rehearsal 3 completed (offline/fallback test with `DEMO_MODE=true`)
- [ ] Backup screen-recording video saved locally

---

## 6. References & Citations
### Straw-to-Grain Ratio (Peer-Reviewed)
- **Hiloidhari, M., Das, D., & Baruah, D. C. (2014).** *Bioenergy potential from crop residue biomass in India.* Renewable and Sustainable Energy Reviews, 32, 504–512. (Establishes standard residue-to-product ratio of ~1.5 for rice/paddy in Indian biomass assessments.)
- **Gadde, B., Bonnet, S., Menke, C., & Garivait, S. (2009).** *Air pollutant emissions from rice straw open field burning in India, Thailand, and the Philippines.* Environmental Pollution, 157(5), 1554–1558. (Quantifies regional rice straw generation and open-field burning emissions using straw-to-grain ratios.)

### Data Sources & Policy
- **Sentinel-2 (Copernicus):** https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2
- **NASA FIRMS (Active Fire Data):** https://firms.modaps.eosdis.nasa.gov
- **ERA5 (Copernicus Climate Data Store):** https://cds.climate.copernicus.eu
- **Google Earth Engine:** https://earthengine.google.com
- **India Meteorological Department (IMD):** https://mausam.imd.gov.in
- **CAQM Preparedness Press Release (2026):** https://caqm.nic.in/WriteReadData/LINKS/CAQM%20PR%2007_05_2026%20(PDF)
