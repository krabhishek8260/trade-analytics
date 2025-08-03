# Changelog

All notable changes to the Trade Analytics application will be documented in this file.

## [Unreleased]

### Added
- **New Data Detection System**: Smart background data checking without page refreshes
  - Background data monitoring every 30 seconds (configurable)
  - Visual indicators when new data is available
  - Manual refresh option to load new data when ready
  - User controls to enable/disable checking and adjust intervals
  - Implemented across Dashboard, Analysis Tab, and P&L Analytics pages
  - Reduces server load by only checking for changes, not loading full UI
  - Maintains user's current view and scroll position

### Changed
- **Auto-refresh disabled by default**: Pages no longer automatically refresh to prevent disruption
- **Improved user experience**: Users now control when to see updated data
- **Better performance**: Reduced unnecessary API calls and page reloads

### Technical Improvements
- Added data hashing mechanism for efficient change detection
- Implemented background data checking with configurable intervals
- Added visual feedback system with notification banners and button indicators
- Created comprehensive documentation for the new system

## [Previous Versions]

*Note: This changelog was started with the new data detection system implementation. Previous changes are not documented here.* 