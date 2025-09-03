# Doss-Gollin Lab GitHub Pages Website

The Doss-Gollin Research Group website is a Quarto-based academic website that automatically generates publication pages from BibTeX files and includes blog posts, people profiles, and research information. The site is built using Quarto, Python for bibliography processing, and deployed to GitHub Pages.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap and Build Environment
- Install Quarto CLI (tested with v1.4.557):
  ```bash
  wget -q https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.557/quarto-1.4.557-linux-amd64.tar.gz
  sudo tar -xzf quarto-1.4.557-linux-amd64.tar.gz -C /opt
  sudo ln -sf /opt/quarto-1.4.557/bin/quarto /usr/local/bin/quarto
  ```

- Initialize git submodules (contains bibliography files):
  ```bash
  git submodule init
  git submodule update
  ```

- Set up conda environment with Python dependencies:
  ```bash
  conda env create -f _environment.yml
  conda activate dossgollin-lab
  ```

### Build the Website
- Generate publication pages from BibTeX files:
  ```bash
  conda activate dossgollin-lab
  python bibtex_to_qmd.py
  ```

- **Build the complete website - NEVER CANCEL: Takes ~60 seconds, set timeout to 180+ seconds:**
  ```bash
  conda activate dossgollin-lab
  time quarto render  # Expected time: 57 seconds
  ```

- **Start preview server for development:**
  ```bash
  conda activate dossgollin-lab
  quarto preview --port 4200 --host 0.0.0.0
  # Available at http://localhost:4200
  ```

### Code Quality and Linting
- **Always run Python formatting before committing changes:**
  ```bash
  conda activate dossgollin-lab
  black bibtex_to_qmd.py
  ```

- **Run type checking (expected to show import warnings):**
  ```bash
  conda activate dossgollin-lab
  mypy bibtex_to_qmd.py  # Warnings about missing type stubs are expected
  ```

## Validation Requirements

### Manual Testing Scenarios
After making any changes, **ALWAYS** test the following scenarios to ensure functionality:

1. **Build and Preview Test:**
   - Complete full build process (quarto render)
   - Start preview server and verify it loads at http://localhost:4200
   - Take a screenshot to verify visual functionality

2. **Navigation Test:**
   - Test all main navigation links: People, Publications, Research, Teaching, Join Us, Contact
   - Verify Publications page shows articles in tabbed format
   - Test filtering and sorting functionality on publications

3. **Bibliography Generation Test:**
   - Run `python bibtex_to_qmd.py` without errors
   - Verify publication QMD files are generated in publications/* directories
   - Check that publication pages render correctly with proper metadata

4. **Content Validation:**
   - Verify recent blog posts appear on homepage news listing
   - Check that people profiles load correctly
   - Ensure images and links work properly

### Critical Timing Expectations
- **Build time: ~57 seconds - NEVER CANCEL builds before 120 seconds minimum**
- **Preview server startup: ~5 seconds**
- **Bibliography generation: ~1 second**  
- **Python linting: <1 second**

## Repository Structure

### Key Directories and Files
```
/
├── _assets/              # Images, CSS themes, references
├── _bibliography/        # Git submodule with BibTeX files
├── _environment.yml      # Conda environment specification
├── _quarto.yml          # Main Quarto configuration
├── bibtex_to_qmd.py     # Python script to generate publication pages
├── people/              # Individual profile pages
├── posts/               # Blog posts organized by year
├── publications/        # Generated publication pages (auto-created)
└── teaching/            # Course information
```

### Important Files to Know
- **_quarto.yml**: Main website configuration, navigation, and styling
- **bibtex_to_qmd.py**: Processes BibTeX entries into Quarto markdown files
- **_bibliography/my-papers.bib**: BibTeX source file (in git submodule)
- **index.qmd**: Homepage with news listing
- **Makefile**: Contains Docker-based Jekyll commands (LEGACY - DO NOT USE, will fail)

## Common Development Tasks

### Adding New Content
- **Blog posts**: Create new `.qmd` file in `posts/YYYY/` directory
- **People profiles**: Add `.qmd` file in appropriate `people/` subdirectory  
- **Publications**: Update BibTeX file in `_bibliography/` submodule, then run `python bibtex_to_qmd.py`

### Updating Bibliography
```bash
cd _bibliography
git pull origin master
cd ..
python bibtex_to_qmd.py
quarto render
```

### Troubleshooting
- **Build fails**: Check that conda environment is activated and git submodules are initialized
- **Missing publications**: Ensure `python bibtex_to_qmd.py` ran successfully after bibliography updates
- **Images not loading**: Check paths in `_assets/img/` directory
- **Styling issues**: Verify `_assets/theme/theme-rice.scss` is properly configured

### Development Workflow
1. Activate conda environment: `conda activate dossgollin-lab`
2. Make your changes to content files
3. If bibliography changed: run `python bibtex_to_qmd.py`
4. Build and test: `quarto render` (wait full 60+ seconds)
5. Preview changes: `quarto preview --port 4200`
6. Format Python code: `black bibtex_to_qmd.py`
7. Test manually through browser navigation
8. Commit changes

## CI/CD Information
- **GitHub Actions workflow**: `.github/workflows/publish-quarto.yml`
- **Deployment**: Automatic to GitHub Pages on push to master branch
- **Build time in CI**: Similar to local (~60 seconds)
- **Dependencies**: Quarto CLI, conda environment, git submodules

## Performance Notes
- Website renders 132 files during full build
- Publications are generated dynamically from BibTeX
- Images should be optimized for web (PNG/JPG in `_assets/img/`)
- Live reload works during preview for content changes

## Known Issues  
- MyPy shows expected warnings about missing type stubs for bibtexparser and titlecase
- Some template EJS files may show warnings during build (can be ignored)
- CDN resources may be blocked in some environments (doesn't affect functionality)

## What Does NOT Work (Do Not Use)
- **Makefile commands**: The Makefile contains legacy Jekyll Docker commands that will fail. This is now a Quarto site, not Jekyll.
- **Docker-based build**: `make install`, `make build`, and `make devserver` commands will fail with Docker errors.
- **Jekyll workflow**: This repository was converted from Jekyll to Quarto but retains old Makefile for reference.