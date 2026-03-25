---
title: Mobile App Troubleshooting
category: troubleshooting
---

## Mobile App Not Syncing in Background (iOS)

iOS aggressively suspends background processes to save battery. CloudSync may stop syncing when the app is not in the foreground.

**Common causes:**
- iOS Background App Refresh is disabled for CloudSync
- Low Power Mode is active
- Device storage is nearly full (iOS pauses background tasks below 1GB free)
- App was force-quit by the user (swipe up from app switcher)

**Resolution:**
1. Settings > General > Background App Refresh > enable for CloudSync
2. Disable Low Power Mode: Settings > Battery
3. Free up device storage (at least 2GB recommended)
4. Open the CloudSync app periodically to trigger sync
5. Enable push notifications for CloudSync to keep the background connection alive

**Note:** iOS does not guarantee background execution. For critical syncs, open the app and keep it in the foreground until complete.

## Mobile App Not Syncing in Background (Android)

Android battery optimization may kill CloudSync's background process.

**Common causes:**
- Battery optimization is enabled for CloudSync
- Device manufacturer's aggressive memory management (Samsung, Xiaomi, Huawei)
- Android Doze mode suspending network access after device is idle

**Resolution:**
1. Settings > Apps > CloudSync > Battery > set to "Unrestricted"
2. For Samsung: Settings > Device Care > Battery > App Power Management > add CloudSync to "Never sleeping"
3. For Xiaomi: Settings > Apps > CloudSync > Battery Saver > "No restrictions"
4. Disable Data Saver for CloudSync: Settings > Network > Data Saver > Unrestricted
5. Lock CloudSync in recent apps (long-press on the app card > Lock)

**Manufacturer-specific guides:** https://docs.cloudsync.io/mobile/android-battery

## Photo Auto-Backup Not Working

The mobile app's photo backup feature may silently stop working.

**Common causes:**
- Photo access permission revoked or set to "Limited" (iOS) / "Allow only while using the app" (Android)
- Backup set to "Wi-Fi only" and device is on cellular
- Storage quota exceeded (server-side)
- Backup folder was deleted or renamed on the cloud

**Resolution:**
1. Check photo permissions: grant "Full Access" (iOS) or "Allow all the time" (Android)
2. Verify backup settings: CloudSync app > Settings > Photo Backup
3. Check storage quota: CloudSync app > Account > Storage
4. If backup folder is missing, go to Settings > Photo Backup > "Reset Backup Folder"
5. Force a manual backup: Photos tab > pull down to refresh

## Mobile App Crashes on Launch

The CloudSync mobile app crashes immediately or within seconds of opening.

**Common causes:**
- Corrupted local cache or database
- App version incompatible with OS version
- Insufficient device memory (RAM)

**Resolution:**
1. Force-close the app and reopen
2. Clear app cache: (Android) Settings > Apps > CloudSync > Storage > Clear Cache
3. For iOS: delete and reinstall the app (Settings > Storage > CloudSync > Delete App)
4. Update to the latest app version from App Store / Play Store
5. Check minimum OS requirements: iOS 15+ / Android 10+
6. If persistent, collect crash logs: CloudSync app > Settings > About > "Send Diagnostic Report"

## Offline Files Not Available

Files marked for offline access are not available when the device has no connection.

**Common causes:**
- File was marked offline but download did not complete before going offline
- Device storage is full - offline file was evicted to free space
- The file was updated on the cloud but the offline copy was not refreshed

**Resolution:**
1. While online, check offline status: file should show a green checkmark icon
2. If no checkmark, tap the file > "Make Available Offline" again and wait for download
3. Free up device storage - offline files need reserved space
4. Go to Settings > Offline Files > "Refresh All" to re-download latest versions
5. Check Settings > Offline Files > Storage Limit - increase if possible
