# Development Notes

## Authentication System
- Uses username + token for better entropy (~31 bits)
- No IP logging, maximum anonymity
- Stores only username and language preference
- 3 permanent tokens and 50 one-time tokens per user
- Username generation uses syllable combinations (CV format)
- Token collisions handled with regeneration
- 3-syllable namespace (~250k) sufficient for practical use

## Design Decisions
- Local Bootstrap files preferred over CDN
- Template organization in subdirectories (auth/, forum/, wiki/)
- CSRF protection required across forms
- Database uses context managers for connections
- Style centralized in styles.css

## Scaling Strategy
- Target community size ~1000 active users
- When needed, split into specialized forums
- Maintain single authentication across all forums
- Shared login system for forum and wiki access
- No complex filtering initially

## Fixed Issues
- CSRF token handling in forms
- Database connection management
- Template directory structure
- Registration/confirmation flow
- Token uniqueness checking

## To Test
- Thread creation
- Posting functionality
- Private threads
- Edit history
- Image handling
- Translation features

## Future Considerations
- Wiki implementation
- Forum specialization
- Token system monitoring
- Image size limits (1200px max)
- Markdown with image support

## Security Notes
- No personal data stored
- No tracking beyond essential functionality
- Private threads without revealing participant identities
- Token entropy sufficient for security without compromising anonymity
