# Week 7 Pull Request

## Summary of Changes

### Unified Scoring System
- Implemented centralized configuration for suspicion thresholds and weights
- Fixed threshold synchronization between UI and backend
- Ensured consistent scoring across all components

### Evidence Collection Improvements
- Fixed metadata recording for flagged events
- Implemented cropped region saving for suspicious objects
- Added complete behavior details to evidence metadata
- Optimized file-based evidence storage system

### Bug Fixes
- Fixed unauthorized object detection scoring
- Corrected score conversion from 0-1 to 0-100 scale
- Resolved max_suspicion scope issues

## Testing
- Verified unauthorized object detection shows correct scores in metadata
- Confirmed UI threshold changes are properly applied to backend
- Tested evidence saving with complete metadata and cropped regions

## Files Modified
- src/detection/suspicion_scorer.py
- src/detection/flagged_evidence_saver.py
- src/cheat_detection_web_app/app.py
- src/cheat_detection_web_app/static/script.js
