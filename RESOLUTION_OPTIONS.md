# Higher Resolution Satellite Imagery Options

## Your Current Setup
- **Dataset**: Sentinel-2 (10m resolution)
- **Quality**: Good for regional mapping, but limited detail for fine objects
- **Issue**: Roads, small buildings, and fine features are slightly blurred

## 📊 Available Options (Best to Fastest)

### Option 1: Pan-sharpened Sentinel-2 ✅ RECOMMENDED
**Script**: `11_collect_dhaka_pansharpened.py`

- **Resolution**: 10m (same) with **significantly sharper detail**
- **Method**: High-pass filter technique using B8A band
- **Quality**: Sharp edges for roads, building outlines, clear boundaries
- **Processing**: Fast (~2-5 min per image in GEE)
- **Cost**: Free (within GEE limits)
- **Best for**: Detail improvement without changing datasets

**Run it:**
```bash
python scripts/11_collect_dhaka_pansharpened.py
```

---

### Option 2: Landsat 8 Pan-sharpened
- **Resolution**: 30m base, sharpened with 15m pan → effective ~15m detail
- **Method**: USGS Landsat pan-sharpening
- **Quality**: Good for large features (major roads, large buildings)
- **Processing**: Very fast
- **Cost**: Free
- **Best for**: Quick previews, faster downloads

**Pros**: Faster, free
**Cons**: Lower resolution than Sentinel-2

---

### Option 3: Planet Labs (HIGHEST DETAIL) 🌍
- **Resolution**: 3m multispectral, 0.7m panchromatic available
- **Method**: Commercial satellite constellation
- **Quality**: Individual trees, car-level detail on roads
- **Processing**: Slower (requires API)
- **Cost**: Paid subscription (~$1-10 per km²)
- **Best for**: Training fine-grained models (car detection, tree species)

**Setup needed:**
1. Create Planet Labs account
2. Get API key
3. Update script with credentials

---

### Option 4: High-Resolution GEE Imagery (If available)
- **Airbus OneAtlas**: 1.5m resolution
- **Maxar WorldView**: 0.3-1m resolution
- **Issue**: Limited free availability, regional restrictions

---

## 🎯 My Recommendation: Start with Option 1

**Pan-sharpened Sentinel-2** gives you:
- ✅ Same 10m resolution with **much sharper edges**
- ✅ Better road/building distinction
- ✅ No additional authentication needed
- ✅ Works with your existing GEE pipeline
- ✅ Noticeable quality improvement
- ✅ Free and fast

---

## How Pan-sharpening Works

The algorithm:
1. Extracts RGB bands (B4, B3, B2)
2. Uses B8A (red edge) as pseudo-panchromatic reference
3. Creates high-pass filter (detail-only image)
4. Adds detail back to RGB bands
5. Result: Sharper edges, better definition

**Before**: Slightly blurred boundaries between objects
**After**: Clear, crisp edges for roads and buildings

---

## Usage Instructions

### Step 1: Run Pan-sharpened Collection
```bash
python scripts/11_collect_dhaka_pansharpened.py
```

### Step 2: Check Local Previews
Look in: `data/dhaka_pansharpened_previews/`
- PNG thumbnails show before/after quality
- Use these to decide if you want higher resolution

### Step 3: Monitor Export Tasks
- Tasks export to Google Drive: `dhaka_pansharpened/images/`
- GeoTIFF format with metadata
- Typically completes in 30-60 minutes

### Step 4: Download & Process
Once exports complete, download from Google Drive and process as usual

---

## Comparison Table

| Dataset | Resolution | Detail Level | Cost | Processing Time | Best For |
|---------|-----------|--------------|------|-----------------|----------|
| **Sentinel-2 (current)** | 10m | Medium | Free | Fast | Regional scale |
| **Pan-sharpened S2** | 10m + detail | Medium-High | Free | 2-5 min | Object boundaries ✅ |
| **Landsat 8** | 15-30m | Low-Medium | Free | Very fast | Quick preview |
| **Planet Labs** | 3m | Very High | Paid | Slow | Fine-grained features |
| **WorldView** | 0.3-1m | Extreme | Paid | Very slow | Precision mapping |

---

## Next Steps

1. **Try pan-sharpening** → Run script 11 and compare previews
2. **If satisfied**: Process and use for training
3. **If need higher resolution**: Set up Planet Labs integration
4. **If need specific areas**: Can modify AOI coordinates in script

Questions? Check the script comments or GEE documentation.
