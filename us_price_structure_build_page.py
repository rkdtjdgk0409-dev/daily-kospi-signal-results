#!/usr/bin/env python3
from price_structure_workspace import MarketPageConfig, build_market_page


def main() -> None:
    build_market_page(
        MarketPageConfig(
            result_dir="us_price_structure_results",
            docs_dir="docs/us-price-structure",
            page_title="US Chart Structure",
            market_name="미국 시장",
            currency_symbol="$",
            currency_decimals=2,
            market_options=("S&P 500", "NASDAQ-100"),
            market_match_mode="contains",
            home_href="../us/",
            other_market_href="../",
            position_href="../us-position/",
            scanner_href="./",
            other_market_label="한국 시장",
        )
    )


if __name__ == "__main__":
    main()
