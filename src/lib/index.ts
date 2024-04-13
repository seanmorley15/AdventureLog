// place files you want to import through the `$lib` alias in this folder.
export function countryCodeToName(countryCode: string) {
  switch (countryCode) {
    case "us":
      return "United States";
    case "de":
      return "Germany";
    case "fr":
      return "France";
    case "gb":
      return "United Kingdom";
    case "ar":
      return "Argentina";
    case "mx":
      return "Mexico";
    case "jp":
      return "Japan";
    case "cn":
      return "China";
    case "in":
      return "India";
    case "au":
      return "Australia";
    case "nz":
      return "New Zealand";
    case "za":
      return "South Africa";
    case "eg":
      return "Egypt";
    case "ca":
      return "Canada";
    case "br":
      return "Brazil";
  }
}

export function getFlag(country: string) {
  return `https://flagcdn.com/h24/${country}.png`;
}
    
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

const inspirationalQuotes = [
  "Believe you can and you're halfway there. - Theodore Roosevelt",
  "The only way to do great work is to love what you do. - Steve Jobs",
  "In the middle of every difficulty lies opportunity. - Albert Einstein",
  "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
  "It does not matter how slowly you go as long as you do not stop. - Confucius",
  "Success is not final, failure is not fatal: It is the courage to continue that counts. - Winston Churchill",
  "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt",
  "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
  "You are never too old to set another goal or to dream a new dream. - C.S. Lewis",
  "The only person you are destined to become is the person you decide to be. - Ralph Waldo Emerson",
  "Happiness is not something ready-made. It comes from your own actions. - Dalai Lama",
  "Life is what happens when you're busy making other plans. - John Lennon",
  "You miss 100% of the shots you don't take. - Wayne Gretzky",
  "The best time to plant a tree was 20 years ago. The second best time is now. - Chinese Proverb",
  "The only way to achieve the impossible is to believe it is possible. - Charles Kingsleigh",
  "Don't count the days, make the days count. - Muhammad Ali",
  "You don't have to be great to start, but you have to start to be great. - Zig Ziglar",
  "You can't go back and change the beginning, but you can start where you are and change the ending. - C.S. Lewis",
  "Dream big and dare to fail. - Norman Vaughan",
  "The secret of getting ahead is getting started. - Mark Twain",
  "Everything you can imagine is real. - Pablo Picasso",
  "You must be the change you wish to see in the world. - Mahatma Gandhi",
  "If you want to lift yourself up, lift up someone else. - Booker T. Washington",
  "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson",
  "The journey of a thousand miles begins with one step. - Lao Tzu",
  "Life isn't about waiting for the storm to pass, it's about learning to dance in the rain. - Vivian Greene",
  "You are never too old to set another goal or to dream a new dream. - Les Brown",
  "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
  "Don't let yesterday take up too much of today. - Will Rogers",
  "The only thing standing between you and your goal is the story you keep telling yourself as to why you can't achieve it. - Jordan Belfort",
  "The future belongs to those who prepare for it today. - Malcolm X",
  "The greatest glory in living lies not in never falling, but in rising every time we fall. - Nelson Mandela",
  "It's not what happens to you, but how you react to it that matters. - Epictetus",
  "The only way to do great work is to love what you do. - Steve Jobs",
  "When one door of happiness closes, another opens, but often we look so long at the closed door that we do not see the one that has been opened for us. - Helen Keller",
  "The only thing that stands between you and your dream is the will to try and the belief that it is actually possible. - Joel Brown",
  "Success is walking from failure to failure with no loss of enthusiasm. - Winston Churchill",
  "Believe in yourself! Have faith in your abilities! Without a humble but reasonable confidence in your own powers you cannot be successful or happy. - Norman Vincent Peale",
  "The greatest adventure is what lies ahead. - J.R.R. Tolkien",
  "The only way to do great work is to love what you do. - Steve Jobs",
  "What you get by achieving your goals is not as important as what you become by achieving your goals. - Zig Ziglar",
  "To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment. - Ralph Waldo Emerson",
  "What lies behind us and what lies before us are tiny matters compared to what lies within us. - Ralph Waldo Emerson",
  "The only person you are destined to become is the person you decide to be. - Ralph Waldo Emerson",
  "The best and most beautiful things in the world cannot be seen or even touched - they must be felt with the heart. - Helen Keller",
  "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt",
  "It always seems impossible until it is done. - Nelson Mandela",
  "I can't change the direction of the wind, but I can adjust my sails to always reach my destination. - Jimmy Dean",
  "Believe you can and you're halfway there. - Theodore Roosevelt",
  "The only way to achieve the impossible is to believe it is possible. - Charles Kingsleigh",
  "If you're going through hell, keep going. - Winston Churchill",
  "Nothing is impossible, the word itself says 'I'm possible'! - Audrey Hepburn",
  "The only thing standing in the way between you and your goal is the story you keep telling yourself as to why you can't achieve it. - Jordan Belfort",
  "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
  "Success is not final, failure is not fatal: It is the courage to continue that counts. - Winston Churchill",
  "Keep your face always toward the sunshine - and shadows will fall behind you. - Walt Whitman",
  "Success is not the key to happiness. Happiness is the key to success. If you love what you are doing, you will be successful. - Albert Schweitzer",
  "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
  "You are never too old to set another goal or to dream a new dream. - C.S. Lewis",
  "You are never too old to set another goal or to dream a new dream. - C.S. Lewis",
  "The only person you are destined to become is the person you decide to be. - Ralph Waldo Emerson",
  "Happiness is not something ready-made. It comes from your own actions. - Dalai Lama",
  "Life is what happens when you're busy making other plans. - John Lennon",
  "You miss 100% of the shots you don't take. - Wayne Gretzky",
  "The best time to plant a tree was 20 years ago. The second best time is now. - Chinese Proverb",
  "The only way to achieve the impossible is to believe it is possible. - Charles Kings",
];

export function getRandomQuote() {
  const randomIndex = Math.floor(Math.random() * inspirationalQuotes.length);
  return inspirationalQuotes[randomIndex];
}
