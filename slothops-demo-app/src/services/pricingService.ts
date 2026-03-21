import { getItemDetails } from "./inventoryService";

export function calculateTotalWeight(cartItemIds: string[]): number {
  let totalWeightInKg = 0;

  for (const itemId of cartItemIds) {
    const itemDetails = getItemDetails(itemId);
    
    if (itemDetails) {
      // BUG: itemDetails.weight can be undefined for digital items
      // This crashes with: TypeError: Cannot read properties of undefined (reading 'value')
      totalWeightInKg += itemDetails.weight!.value;
    }
  }

  return totalWeightInKg;
}
