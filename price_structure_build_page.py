#!/usr/bin/env python3
from price_structure_workspace import MarketPageConfig, build_market_page


def main() -> None:
    build_market_page(
        MarketPageConfig(
            result_dir="price_structure_results",
            docs_dir="docs/price-structure",
            page_title="Korea Chart Structure",
            market_name="한국 시장",
            currency_symbol="₩",
            currency_decimals=0,
            market_options=("KOSPI", "KOSDAQ"),
            market_match_mode="equals",
            home_href="../",
            other_market_href="../us/",
            position_href="../position/",
            scanner_href="./",
            other_market_label="미국 시장",
        )
    )


if __name__ == "__main__":
    main()
