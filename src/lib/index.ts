// place files you want to import through the `$lib` alias in this folder.
export function generateRandomString() {
  let randomString = "";
  const digits =
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

  for (let i = 0; i < 10; i++) {
    const randomIndex = Math.floor(Math.random() * digits.length);
    randomString += digits[randomIndex];
  }
  return randomString;
}
