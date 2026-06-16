import argparse
from .pipeline import process_specific_page, process_all_pages_of_manga

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crop & prepare Manga109 panels for ToonCrafter")
    parser.add_argument('--manga', type=str, default='TetsuSan')
    parser.add_argument('--page', type=int, default=None, help="Specific page number (if not set, processes all pages)")
    parser.add_argument('--base', type=str, default='data/raw/Manga109')
    parser.add_argument('--no-vis', action='store_true', help="Disable visualization output")
    
    # FIX: Replaced type=bool with action='store_true'
    parser.add_argument('--remove-text', action='store_true', help="Remove text from panels")
    
    args = parser.parse_args()

    try:
        if args.page is not None:
            # Process single page
            process_specific_page(args.manga, args.page, args.base, create_visualization=not args.no_vis, remove_text=args.remove_text)
        else:
            # Process all pages
            process_all_pages_of_manga(args.manga, args.base, create_visualization=not args.no_vis, remove_text=args.remove_text)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback; traceback.print_exc()