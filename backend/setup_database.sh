#!/bin/bash

# EVF Portugal 2030 - Database Setup Script
# Automates database creation, migration, and seeding
#
# Usage: ./backend/setup_database.sh [options]
#
# Options:
#   --reset     Drop and recreate database
#   --test-only Run only connection tests
#   --seed-only Run only seed script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="evf_portugal_2030"
DB_USER="postgres"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
RESET=false
TEST_ONLY=false
SEED_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --reset)
            RESET=true
            shift
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --seed-only)
            SEED_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--reset] [--test-only] [--seed-only]"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_postgres() {
    if ! command -v psql &> /dev/null; then
        print_error "PostgreSQL client (psql) not found"
        print_info "Install PostgreSQL: brew install postgresql (macOS)"
        exit 1
    fi
    print_success "PostgreSQL client found"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        exit 1
    fi
    print_success "Python 3 found ($(python3 --version))"
}

create_database() {
    print_info "Creating database: $DB_NAME"

    # Check if database exists
    if psql -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        if [ "$RESET" = true ]; then
            print_warning "Database exists - dropping and recreating"
            dropdb -U "$DB_USER" "$DB_NAME" 2>/dev/null || true
            createdb -U "$DB_USER" "$DB_NAME"
            print_success "Database recreated"
        else
            print_info "Database already exists"
        fi
    else
        createdb -U "$DB_USER" "$DB_NAME"
        print_success "Database created"
    fi
}

install_dependencies() {
    print_info "Installing Python dependencies"

    cd "$SCRIPT_DIR"

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment"
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    print_success "Dependencies installed"
}

run_migrations() {
    print_info "Running database migrations"

    cd "$PROJECT_ROOT"

    # Run Alembic migrations
    alembic upgrade head

    print_success "Migrations completed"
}

run_tests() {
    print_info "Running connection tests"

    cd "$PROJECT_ROOT"
    python3 backend/test_connection.py

    print_success "Connection tests completed"
}

seed_data() {
    print_info "Seeding demo data"

    cd "$PROJECT_ROOT"
    python3 backend/seed_data.py

    print_success "Seed data completed"
}

# Main execution
main() {
    print_header "EVF Portugal 2030 - Database Setup"

    # Check prerequisites
    print_info "Checking prerequisites..."
    check_postgres
    check_python
    echo ""

    # Handle test-only mode
    if [ "$TEST_ONLY" = true ]; then
        print_header "Running Connection Tests Only"
        run_tests
        exit 0
    fi

    # Handle seed-only mode
    if [ "$SEED_ONLY" = true ]; then
        print_header "Running Seed Script Only"
        seed_data
        exit 0
    fi

    # Full setup
    print_header "Step 1: Database Creation"
    create_database

    print_header "Step 2: Install Dependencies"
    install_dependencies

    print_header "Step 3: Run Migrations"
    run_migrations

    print_header "Step 4: Test Connection"
    run_tests

    print_header "Step 5: Seed Demo Data"
    seed_data

    # Success message
    print_header "Setup Complete!"
    echo ""
    print_success "Database is ready for use!"
    echo ""
    print_info "Demo credentials:"
    echo "   Email:    admin@demo.pt"
    echo "   Password: Demo@2024"
    echo ""
    print_info "Start the API with:"
    echo "   cd backend"
    echo "   uvicorn main:app --reload --port 8000"
    echo ""
    print_info "API documentation:"
    echo "   http://localhost:8000/docs"
    echo ""
}

# Run main function
main "$@"
