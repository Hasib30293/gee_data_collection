# Multi-Region Data Collection Guide

Collect high-resolution satellite imagery from different regions of Bangladesh to create diverse training datasets without repeating locations.

## 📍 Available Regions

### 1. **Dhaka** - Urban Capital
- **Coordinates**: 23.7-23.9°N, 90.35-90.45°E
- **Characteristics**: Dense urban development, high-rise buildings, major roads, traffic infrastructure
- **Best for**: Urban classification, building detection, road networks
- **Imagery**: High contrast, clear building edges

### 2. **Chittagong** - Coastal Industrial City
- **Coordinates**: 22.2-22.4°N, 91.8-92.0°E
- **Characteristics**: Port facilities, industrial zones, mixed urban-rural, coastal areas
- **Best for**: Industrial area detection, port infrastructure, urban sprawl
- **Imagery**: Diverse land use patterns

### 3. **Sylhet** - Mountainous/Forest Region
- **Coordinates**: 24.8-25.0°N, 91.8-92.0°E
- **Characteristics**: Tea gardens, forests, hilly terrain, water bodies, sparse settlements
- **Best for**: Forest classification, crop type detection, terrain analysis
- **Imagery**: Green vegetation, forest structure detail

### 4. **Khulna** - Sundarbans Delta
- **Coordinates**: 22.8-23.0°N, 89.5-89.7°E
- **Characteristics**: Mangrove forests, water channels, wetlands, tidal areas
- **Best for**: Water body detection, wetland classification, seasonal flooding
- **Imagery**: Complex water patterns, vegetation in water

### 5. **Rajshahi** - Agricultural Heartland
- **Coordinates**: 24.35-24.55°N, 88.55-88.75°E
- **Characteristics**: Paddy fields, agricultural plots, rural settlements, river systems
- **Best for**: Crop classification, agricultural analysis, field boundaries
- **Imagery**: Regular field patterns, seasonal variations

### 6. **Barisal** - River Delta
- **Coordinates**: 22.6-22.8°N, 90.2-90.4°E
- **Characteristics**: River channels, flood plains, seasonal water bodies, low-lying areas
- **Best for**: Flood prediction, river dynamics, delta ecosystems
- **Imagery**: Complex water/land boundaries, seasonal variations

---

## 🚀 Quick Start

### Run Default Collection (3 regions)
```bash
python scripts/12_collect_multi_region.py
```

This collects from: **Dhaka, Chittagong, Sylhet** (default)

### Customize Regions

Edit the script to select different regions:

```python
REGIONS_TO_COLLECT = ["dhaka", "chittagong", "sylhet"]
```

Examples:

**Collect only water regions:**
```python
REGIONS_TO_COLLECT = ["khulna", "barisal"]
```

**Collect agricultural + forest:**
```python
REGIONS_TO_COLLECT = ["rajshahi", "sylhet"]
```

**Collect all 6 regions (comprehensive dataset):**
```python
REGIONS_TO_COLLECT = ["dhaka", "chittagong", "sylhet", "khulna", "rajshahi", "barisal"]
```

**Collect single region:**
```python
REGIONS_TO_COLLECT = ["chittagong"]
```

---

## 📊 Output Organization

After running, your data is organized by region:

```
data/
├── multi_region_previews/
│   ├── dhaka/          # Dhaka previews
│   │   ├── dhaka_pansharp_20230515_000_preview.png
│   │   └── ...
│   ├── chittagong/     # Chittagong previews
│   │   ├── chittagong_pansharp_20230602_000_preview.png
│   │   └── ...
│   ├── sylhet/         # Sylhet previews
│   └── ...
│
└── multi_region_metadata/
    ├── dhaka/
    ├── chittagong/
    ├── sylhet/
    └── ...

Google Drive:
└── multi_region_images/
    ├── dhaka/          # Dhaka GeoTIFF exports
    ├── chittagong/     # Chittagong GeoTIFF exports
    ├── sylhet/         # Sylhet GeoTIFF exports
    └── ...
```

---

## 🎯 Collection Strategy

### For Balanced Training Data
1. Collect from each region equally
2. Mix urban, rural, water, and forest classes
3. Rotate through regions in multiple runs

### For Specific Classification
| Classification Goal | Recommended Regions |
|---|---|
| Urban detection | Dhaka, Chittagong |
| Water/Flood | Khulna, Barisal |
| Agriculture | Rajshahi, Sylhet |
| Forest | Sylhet, Khulna (mangrove) |
| Mixed scenes | All regions |

### Multi-Run Rotation Strategy
```bash
# Run 1: Urban focus
python scripts/12_collect_multi_region.py  # Edit to: dhaka, chittagong

# Run 2: Water focus  
python scripts/12_collect_multi_region.py  # Edit to: khulna, barisal

# Run 3: Agriculture focus
python scripts/12_collect_multi_region.py  # Edit to: rajshahi

# Run 4: Forest focus
python scripts/12_collect_multi_region.py  # Edit to: sylhet
```

---

## 🔍 Image Quality Features

### Pan-sharpening Benefits per Region

| Region | Sharp Details Visible |
|---|---|
| **Dhaka** | Individual buildings, road lanes, parking lots |
| **Chittagong** | Port containers, ship positions, warehouse structures |
| **Sylhet** | Tea garden rows, individual tree clusters, water bodies |
| **Khulna** | Water channel networks, vegetation boundaries |
| **Rajshahi** | Individual field boundaries, crop patterns |
| **Barisal** | River channel complexity, island formations |

### What You Get
- **Resolution**: 10m pixels
- **Detail**: Pan-sharpened (sharp edges)
- **Coverage**: Full RGB + metadata
- **Format**: GeoTIFF (georeferenced)
- **Cloud filter**: <5% cloud cover only

---

## 📋 Manifest File

After collection, check `data/multi_region_manifest.json`:

```json
{
  "timestamp": "2024-05-15T10:30:00",
  "regions_collected": 3,
  "total_tasks": 90,
  "regions": [
    {
      "region": "dhaka",
      "region_name": "Dhaka Metropolitan",
      "exported": 30,
      "previews": 30,
      "task_ids": [...]
    },
    ...
  ]
}
```

Use this to track:
- How many images from each region
- Export task IDs for monitoring
- Which regions were processed

---

## 💡 Tips

1. **Different times of year**: Satellite data spans 2023-2024, captures seasonal variations
2. **Cloud-free imagery**: Only <5% cloud cover selected
3. **Most recent first**: Images sorted by date (newest first)
4. **No duplicates**: Each run collects different acquisition dates
5. **Organize on Drive**: Google Drive automatically organizes by region folder

---

## ⚠️ Important Notes

- Edit script **before** running to select regions
- Each region can have up to 30 images (MAX_IMAGES_PER_REGION)
- Google Drive exports happen in parallel (30-60 min typical)
- Local previews download immediately for preview
- Monitor exports in Google Earth Engine Code Editor or Drive

---

## Example Workflows

### Workflow 1: Quick Test
```bash
# Collect from single region
# Edit: REGIONS_TO_COLLECT = ["dhaka"]
python scripts/12_collect_multi_region.py
```
**Time**: 5-10 min, ~30 images, check previews

### Workflow 2: Balanced Dataset
```bash
# Collect from all 6 regions over time
# Run 1: Edit REGIONS_TO_COLLECT = ["dhaka", "chittagong", "sylhet"]
python scripts/12_collect_multi_region.py

# Run 2: Edit REGIONS_TO_COLLECT = ["khulna", "rajshahi", "barisal"]
python scripts/12_collect_multi_region.py
```
**Total**: ~180 images, diverse coverage

### Workflow 3: Comprehensive Collection
```bash
# Get all regions in one run
# Edit: REGIONS_TO_COLLECT = ["dhaka", "chittagong", "sylhet", "khulna", "rajshahi", "barisal"]
python scripts/12_collect_multi_region.py
```
**Total**: ~180 images, maximum diversity

---

Need a specific region added or modified? Let me know the coordinates and I'll add it!
