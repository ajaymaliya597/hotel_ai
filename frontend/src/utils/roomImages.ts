const FALLBACK_ROOM_IMAGE = "https://images.pexels.com/photos/6466496/pexels-photo-6466496.jpeg?auto=compress&cs=tinysrgb&h=650&w=940";

const ROOM_IMAGES: Record<string, string> = {
  "Standard Queen": "https://images.pexels.com/photos/6394607/pexels-photo-6394607.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
  "Deluxe King": "https://images.pexels.com/photos/6434592/pexels-photo-6434592.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
  "Family Suite": "https://images.pexels.com/photos/2736384/pexels-photo-2736384.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
  "Premium Suite": "https://images.pexels.com/photos/8082217/pexels-photo-8082217.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
};

export function roomImageFor(roomType: string): string {
  return ROOM_IMAGES[roomType] ?? FALLBACK_ROOM_IMAGE;
}
