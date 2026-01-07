# Setup Script for R Portfolio Optimization App
# Run this script once to install all required packages

cat("═══════════════════════════════════════════════════\n")
cat("  R Portfolio Optimization App - Setup Script\n")
cat("═══════════════════════════════════════════════════\n\n")

# List of required packages
required_packages <- c(
  "shiny",
  "shinydashboard",
  "quantmod",
  "PerformanceAnalytics",
  "PortfolioAnalytics",
  "plotly",
  "DT",
  "tidyverse",
  "xts",
  "lubridate",
  "quadprog"
)

cat("Checking for required packages...\n\n")

# Check which packages need to be installed
packages_to_install <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]

if (length(packages_to_install) > 0) {
  cat(sprintf("Installing %d missing packages:\n", length(packages_to_install)))
  cat(paste("  -", packages_to_install, collapse = "\n"), "\n\n")

  # Install missing packages
  install.packages(packages_to_install, dependencies = TRUE)

  cat("\n✓ Package installation complete!\n\n")
} else {
  cat("✓ All required packages are already installed!\n\n")
}

# Verify installation
cat("Verifying package installation...\n\n")

all_installed <- TRUE
for (pkg in required_packages) {
  if (requireNamespace(pkg, quietly = TRUE)) {
    cat(sprintf("  ✓ %s\n", pkg))
  } else {
    cat(sprintf("  ✗ %s - FAILED\n", pkg))
    all_installed <- FALSE
  }
}

cat("\n")

if (all_installed) {
  cat("═══════════════════════════════════════════════════\n")
  cat("  ✓ Setup Complete!\n")
  cat("═══════════════════════════════════════════════════\n\n")
  cat("You can now run the app with:\n")
  cat("  shiny::runApp('app.R')\n\n")

  # Check for Wilshire stocks file
  if (file.exists("Wilshire-5000-Stocks.csv")) {
    cat("✓ Wilshire-5000-Stocks.csv found\n\n")
  } else {
    cat("⚠ WARNING: Wilshire-5000-Stocks.csv not found\n")
    cat("  Please ensure this file is in the current directory\n\n")
  }

  # Create stock_data directory if it doesn't exist
  if (!dir.exists("stock_data")) {
    dir.create("stock_data")
    cat("✓ Created 'stock_data' directory for caching\n\n")
  }

} else {
  cat("═══════════════════════════════════════════════════\n")
  cat("  ✗ Setup Failed\n")
  cat("═══════════════════════════════════════════════════\n\n")
  cat("Some packages failed to install.\n")
  cat("Please try installing them manually:\n\n")
  cat("install.packages(c(\n")
  cat(paste("  '", required_packages, "'", sep = "", collapse = ",\n"))
  cat("\n))\n\n")
}
