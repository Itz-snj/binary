import { getItemDetails } from "./inventoryService";

export function calculateTotalWeight(cartItemIds: string[]): number {
  let totalWeightInKg = 0;

  for (const itemId of cartItemIds) {
    const itemDetails = getItemDetails(itemId);
    
    if (itemDetails) {
      totalWeightInKg += itemDetails.weight?.value ?? 0;
    }
  }

  return totalWeightInKg;
}
