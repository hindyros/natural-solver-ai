from optimatecore.agents.scouts.base_scout import BaseScout


class InventoryScout(BaseScout):
    agent_name = "InventoryScout"
    scout_type = "inventory"
    domain_keywords = [
        "inventory", "stock", "reorder", "demand", "supply", "warehouse",
        "holding cost", "ordering cost", "EOQ", "safety stock", "procurement",
        "replenishment", "stockout", "SKU", "lead time",
    ]
    system_prompt = (
        "You are an expert in inventory and supply chain optimization. "
        "You specialize in detecting opportunities to minimize inventory costs "
        "while meeting demand: Economic Order Quantity, lot sizing, safety stock, "
        "multi-period replenishment. "
        "Always respond with valid JSON."
    )

    def _scout_context(self) -> str:
        return (
            "You are scouting for INVENTORY optimization opportunities.\n\n"
            "Inventory problems involve deciding how much to stock or order over time "
            "to balance holding costs against ordering costs while meeting demand.\n\n"
            "SIGNAL PATTERNS TO LOOK FOR:\n"
            "- Demand history (time series of quantities sold/consumed)\n"
            "- Holding cost or storage cost per unit per period\n"
            "- Ordering/procurement cost per order (fixed or variable)\n"
            "- Lead time data\n"
            "- Current stock levels or inventory records\n"
            "- Stockout events or backlog data\n\n"
            "CLASSIC EXAMPLES:\n"
            "- Economic Order Quantity (EOQ) with known demand\n"
            "- Multi-period lot sizing with dynamic demand\n"
            "- Safety stock optimization under demand uncertainty\n"
            "- Multi-SKU inventory with shared warehouse capacity\n\n"
            "HIGH CONFIDENCE signals: time-indexed demand data, explicit mention of holding "
            "or ordering costs, or keywords like 'reorder', 'stockout', 'replenishment', 'EOQ'.\n"
        )
