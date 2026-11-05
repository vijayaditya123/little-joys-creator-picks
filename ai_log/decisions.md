# AI Log — Step 6 Brief Corrections

_Documents every claim the LLM invented that was not in the data,_
_and how it was handled._

---

## sia_3vedi (CR-05)

**Model:** qwen/qwen3.8-27b  
**Product:** Nutrimix (milk-mix powder)  

**Raw LLM output:**
```
CONCEPT: Shivanya is rushing to get ready for school and complains that her mom's roti has no "power" for her day. She dramatically pulls out Nutrimix, mixes it into her milk in just 10 minutes, and takes a big sip. She reacts with surprise that the taste hasn't changed at all, then confidently declares she is now ready to conquer the day, highlighting the extra protein boost.
OPENING LINE: Arre mummy, aaj school mein mujhe itni taqat chahiye, bas ek chhota sa secret hai jisse main ready hoon!
TALKING POINTS:
- Dekho, sirf 10 minute mein ready ho gaya, aur taste bilkul wahi hai, koi badlav nahi!
- Isme har scoop mein 12g extra protein hai, jo mere liye bohot zaroori hai.
- Yeh 100% plant protein hai aur isme koi added sugar ya preservatives nahi hain, toh main bina tension ke khata hoon.
CLAIM TO AVOID: Do not mention specific medical benefits or claim it cures any deficiency, as this is a food product and the creator is a child performer, not a medical professional.
SUGGED CAPTION: School ke liye ready hona ab aasaan hai! 🎒 Nutrimix ke saath paao 12g extra protein bina taste change kiye. Try karo aaj hi aur dekho kaise taste same rehta hai! #LittleJoys #Nutrimix #KidsNutrition
```

**Unverified claims (1) — not found in claims_made, flagged and removed:**
- `arre mummy, aaj school mein mujhe itni taqat chahiye, bas ek chhota sa secret hai jisse main ready hoon! - dekho, sirf 10 minute mein ready ho gaya, a`

**Action:** These lines were not included in the final brief.
The concept and opening line in outputs/briefs.md use only
data-backed language from the claims_made column, and no
AVOID_CLAIMS language.

---

## raja_choudhary04 (CR-11)

**Model:** qwen/qwen3.8-27b  
**Product:** Nutrimix (milk-mix powder)  

**Raw LLM output:**
```
CONCEPT: The video opens with a candid, unscripted moment of the child playing or interacting with the parent, seamlessly transitioning into the kitchen where the parent is preparing a simple meal like roti or dosa. The child is present in the frame throughout, observing and then tasting the food, reacting naturally to the flavor without any forced enthusiasm. The product is introduced casually as a routine addition to the daily diet, highlighting its ease of use and lack of taste alteration, keeping the tone warm and domestic rather than promotional.

OPENING LINE: "Aaj subah uthke hi socha ki bachchon ko kya khilau, aur phir hi yaad aaya Nutrimix."

TALKING POINTS:
- "Ek scoop mein 12g plant protein hota hai jo pea, brown rice, aur soy se banta hai, isliye humari roti ka taste bilkul waisa hi rehta hai, koi badlav nahi hota."
- "9 saal ke bachon ko din mein kam se kam 24g protein chahiye, jo ki lagbhag 7-8 katori dal ke barabar hai, aur do scoops Nutrimix milk ke saath lene se protein almost do ande ke barabar milta hai."
- "Isme 23 vitamins aur minerals hain, koi added sugar ya preservatives nahi, aur sirf 10 minute mein ready ho jata hai, isliye bachche khud baar-baar maangte hain kyunki unhe taste pasand hai."

CLAIM TO AVOID: Do not make specific medical health claims or state that the product treats any deficiency, as this creator is a lifestyle vlogger, not a medical professional, which would feel foreign to their audience.

SUGGED CAPTION: "Ghar ke khane mein protein badhane ka sabse aasan tareeka! 🥣🌱 Nutrimix ke saadha roti ya dosa banayein, taste waisa hi rahega aur bachche khush honge. Link bio mein hai, aaj hi try karein!"
```

**Unverified claims (3) — not found in claims_made, flagged and removed:**
- `" - "ek scoop mein 12g plant protein hota hai jo pea, brown rice, aur soy se banta hai, isliye humari roti ka taste bilkul waisa hi rehta hai, koi bad`
- `"
- "9 saal ke bachon ko din mein kam se kam 24g protein chahiye, jo ki lagbhag 7-8 katori dal ke barabar hai, aur do scoops nutrimix milk ke saath le`
- `"
- "isme 23 vitamins aur minerals hain, koi added sugar ya preservatives nahi, aur sirf 10 minute mein ready ho jata hai, isliye bachche khud baar-ba`

**Action:** These lines were not included in the final brief.
The concept and opening line in outputs/briefs.md use only
data-backed language from the claims_made column, and no
AVOID_CLAIMS language.

---

## paediatrics_decoded (CR-16)

**Model:** qwen/qwen3.8-27b  
**Product:** Nutrimix (milk-mix powder)  

**Raw LLM output:**
```
CONCEPT: The doctor sits in his office, addressing a common parental worry about kids not getting enough protein from regular meals. He introduces Nutrimix as a simple, plant-based solution that can be mixed into everyday foods like roti or dosa without changing the taste. A child is shown on screen happily eating the meal and reacting positively to the flavor, demonstrating that the product is kid-approved and easy to consume. The video concludes with the doctor reassuring parents that this is a safe, no-added-sugar way to boost daily protein intake.

OPENING LINE: "Maaen aksar puchhti hain ki bachon ko din bhar mein kitna protein chahiye, aur kaise ensure karein ki wo puri tarah se khana khaayein?"

TALKING POINTS:
- 9 saal ke bachon ko din mein kam se kam 24g protein ki zaroorat hoti hai, jo ki lagbhag 7-8 katoris dal ke barabar hai, lekin Nutrimix ke do scoops milk ke saath milane se aapko almost do ande ke barabar protein milta hai.
- Isme 100% plant protein hai jo pea, brown rice, aur soy se banta hai, aur isme koi added sugar ya preservatives nahi hote, isliye yeh aapke bachon ke liye ek safe aur healthy option hai.
- Sabse acchi baat yeh hai ki isse roti, dosa, ya chilla mein milane se taste bilkul change nahi hota, aur bachche ise khushi se khaate hain kyunki unhe iska taste pasand aata hai.

CLAIM TO AVOID: Do not claim that Nutrimix treats or prevents any specific medical condition or disease, as this crosses the line from nutritional support into medical treatment, which is outside the scope of a food product and could be misleading.

SUGGED CAPTION: Kya aapke bachche ka protein intake sahi hai? Nutrimix ke saadhe 10 minute mein ready ho jata hai aur taste bilkul wahi rehta hai. Link bio mein hai, aaj hi try karein!
```

**Unverified claims (1) — not found in claims_made, flagged and removed:**
- `"maaen aksar puchhti hain ki bachon ko din bhar mein kitna protein chahiye, aur kaise ensure karein ki wo puri tarah se khana khaayein?" - 9 saal ke b`

**Action:** These lines were not included in the final brief.
The concept and opening line in outputs/briefs.md use only
data-backed language from the claims_made column, and no
AVOID_CLAIMS language.

---

## raising_zohran (CR-12)

**Model:** qwen/qwen3.8-27b  
**Product:** Little Joys Gummies  

**Raw LLM output:**
```
CONCEPT: A candid, handheld video capturing a real-life moment where the creator's child is struggling to finish their lunch or seems low on energy, followed by the creator introducing Little Joys Gummies as a simple, plant-based fix. The child takes the lead by tasting the gummy on camera, reacting naturally to the flavor, and speaking a short, genuine line about liking it, while the creator explains how this bridges nutritional gaps without added sugar. The tone remains empathetic and low-pressure, positioning the product as a helpful discovery for busy moms rather than a medical solution.
OPENING LINE: "I was so stressed about him not finishing his tiffin today, so I finally tried this trick that actually worked."
TALKING POINTS:
- "These are 100% plant-based with zero added sugar, which is huge for me because I want to bridge his nutritional gaps without the extra sugar."
- "They contain 11+ vitamins and minerals, including B12, D3, and biotin, which support his energy, bone, and hair health."
- "The chicory root fiber helps with digestion and nutrient absorption, so he’s actually getting what he needs from his meals."
CLAIM TO AVOID: Do not claim the gummies "cure" picky eating or guarantee that the child will immediately love all vegetables, as this overpromises a behavioral change that is not supported by the data and feels inauthentic to a parenting mentor persona.
SUGGED CAPTION: If your little one is struggling to get enough nutrients from their daily meals, these plant-based gummies are a game-changer for our routine. They’re zero added sugar and packed with 11+ vitamins to help bridge those gaps. Grab a pack for your family and see the difference!
```

**Claim check:** No unverified or avoid claims detected. Draft used as-is.

---

## radhikabansal0908 (CR-17)

**Model:** qwen/qwen3.8-27b  
**Product:** Nutrimix (milk-mix powder)  

**Raw LLM output:**
```
CONCEPT: A bright, morning kitchen scene where the creator demonstrates making a quick breakfast of rotis or dosas, seamlessly mixing in Nutrimix to boost protein without altering the taste. The child enters the frame, takes a bite, and reacts with genuine delight, highlighting that the food tastes exactly the same as usual. The creator then briefly explains the 12g plant protein benefit while the child enjoys their meal, keeping the tone warm, relatable, and focused on the ease of adding nutrition to daily meals.
OPENING LINE: "If you’re struggling to get enough protein into your little one’s diet without them complaining about the taste, you need to see this hack."
TALKING POINTS:
- "I just add one scoop of Nutrimix to the dough, and it gives them 12g of plant protein from pea, brown rice, and soy, but the roti taste remains completely unchanged."
- "It’s ready in only 10 minutes, and since it has no added sugar or preservatives, I feel good knowing it’s just 100% plant protein mixed into their regular meals."
- "My kid keeps coming back for seconds because they love the taste, and it’s packed with 23 vitamins and minerals to help them hit their daily protein needs."
CLAIM TO AVOID: Do not claim that Nutrimix replaces the need for other protein sources like eggs or dal, as the data only supports it as an additive supplement that provides protein equivalent to specific foods, not a complete replacement.
SUGGED CAPTION: Struggling to hit those protein goals? 🥣 This little trick makes it so easy! Check out the link in bio to grab Nutrimix and make healthy eating effortless. #LittleJoys #Nutrimix #HealthyKids
```

**Unverified claims (1) — not found in claims_made, flagged and removed:**
- `the creator then briefly explains the 12g plant protein benefit while the child enjoys their meal, keeping the tone warm, relatable, and focused on th`

**Action:** These lines were not included in the final brief.
The concept and opening line in outputs/briefs.md use only
data-backed language from the claims_made column, and no
AVOID_CLAIMS language.

---
