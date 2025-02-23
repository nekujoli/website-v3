
## [v3.0.0] - 2024-02-23

### Added
- Token-based authentication system
- Forum with public/private threads
- Image support with automatic resizing
- Post edit history
- Multi-language support
- Browser-side translation with server caching
- Local Bootstrap implementation
- Comprehensive documentation

### Changed
- Moved styling to central styles.css
- Implemented proper database schema
- Added proper security measures

### Fixed
- Forum routes properly organized
- Database schema consistency
- Config imports standardized
- ContentProcessor implementation unified

### Technical Details
- Database schema harmonized across init_db.py and database.py
- Removed duplicate ContentProcessor code
- Fixed missing Config imports
- Moved forum routes from templates to forum.py
- Added proper type hints and docstrings
