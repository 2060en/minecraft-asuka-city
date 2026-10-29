# Asuka Air 塗裝：Gemini 生圖提示詞

給 Gemini（或其他圖像模型）畫 Asuka Air 787-8 塗裝用。提示詞用英文，圖像模型對英文的細節描述比較穩。

## 使用方式

1. 先上傳兩張參考圖，順序固定：
   - Image 1：[`ref-tail-mark.png`](ref-tail-mark.png)，尾翼上的標誌（黑底白線）
   - Image 2：[`lockup-light.png`](lockup-light.png)，標誌加字標
2. 貼上下面其中一段提示詞
3. 結果不對時，一次只修一件事，用文末的修正指令

## 1. 整機，左前方（主圖）

```text
Create a photorealistic aviation photograph in 16:9 landscape format of a Boeing 787-8 Dreamliner wearing the livery of a fictional airline called ASUKA AIR. It must look like a real photo taken by an aviation spotter: full-frame camera, 70–200 mm lens at about 135 mm, f/8, low three-quarter front view of the aircraft's left side, camera about 1.7 m above the ground. The whole aircraft is in frame with the nose pointing to the left, parked on a sunlit concrete apron.

Aircraft accuracy: a real Boeing 787-8 with correct proportions. Slender fuselage, smoothly rounded nose with the distinctive four-pane 787 cockpit windows, large oval passenger windows, four passenger doors per side, long flexible swept wings with raked wingtips and no winglets, two large GE GEnx engines with sawtooth chevron trailing edges on the nacelles, four-wheel main landing gear bogies, tall swept vertical stabilizer.

Livery (follow precisely):
- Front and middle fuselage: clean gloss white.
- Rear fuselage and tail: deep gloss black. The black starts at one clean, straight diagonal line that begins on the belly just behind the wing and slants upward and rearward to meet the top of the fuselage just in front of the vertical tail. Everything behind this line is solid gloss black: the rear fuselage, the tail cone and the entire vertical stabilizer.
- Tail logo: on the black vertical stabilizer, a white logo exactly as in Image 1. Three parallel flowing lines of equal thickness with rounded ends, each a gentle S-curve that starts horizontal at the lower left, rises, and ends horizontal at the upper right. The middle line is the longest; the top and bottom lines are shorter and staggered. One small solid white dot sits just past the right end of the top line. There is no circle or disc around the logo on the tail. The logo sits in the upper middle of the fin and rises toward the trailing edge.
- Rear fuselage graphic: across the black rear fuselage, three long white parallel flowing lines in the same style as the logo but much larger and more stretched, like an ocean current, sweeping from low near the wing upward toward the tail cone. No dot here.
- Wordmark: the text "ASUKA AIR", exactly these letters, uppercase, spelled A-S-U-K-A, space, A-I-R. Black, clean geometric sans-serif, medium weight, wide letter spacing, as in Image 2. It sits on the forward upper fuselage just above the row of passenger windows, starting just behind the first passenger door and running back toward the wing. The letters are about one metre tall.
- Engine nacelles: gloss white with polished metal inlet lips. Wings and horizontal stabilizers: light grey. Landing gear: grey and silver with black tyres.
- Nothing else on the aircraft: no registration number, no flag, no alliance logo, no fern leaf, no spiral motif, no other text or logos.

Setting: a small airport on a subtropical island in the western Pacific, late afternoon. Warm sunlight from the front left, crisp shadows on the concrete, deep blue sky with a few cumulus clouds, lush green hills and a glimpse of turquoise sea in the background, slight heat haze over the apron. Realistic reflections on the glossy black paint, natural colours, very high detail, sharp focus on the aircraft.
```

## 2. 尾翼特寫

```text
Create a photorealistic close-up aviation photograph in 3:2 landscape format of the tail of a Boeing 787-8 Dreamliner in the livery of a fictional airline called ASUKA AIR. Telephoto lens at about 200 mm, shot from the rear left at a slightly low angle, so the vertical stabilizer fills most of the frame, with part of the rear fuselage, the left horizontal stabilizer and the tail cone visible below it.

Livery (follow precisely):
- The entire vertical stabilizer, the rear fuselage and the tail cone are deep gloss black, with realistic sky reflections on the paint.
- On the fin, a crisp white logo exactly as in Image 1: three parallel flowing lines of equal thickness with rounded ends, each a gentle S-curve that starts horizontal at the lower left, rises, and ends horizontal at the upper right. The middle line is the longest; the top and bottom lines are shorter and staggered. One small solid white dot sits just past the right end of the top line. No circle or disc around it. The logo sits in the upper middle of the fin and rises toward the trailing edge.
- On the black rear fuselage below the fin, three long white parallel flowing lines in the same style but larger and stretched, like an ocean current, sweeping upward toward the tail cone. No dot here.
- Horizontal stabilizer: light grey. Visible details: rudder hinge line, panel seams, the APU exhaust at the tail cone, a few rear passenger windows on the black paint.
- No registration number, no flag, no fern leaf, no spiral motif, no other text or logos.

Setting: clear deep blue sky with a few cumulus clouds, late-afternoon sunlight from the left catching the leading edge of the fin. Real photograph, very high detail, sharp focus.
```

## 3. 正側面（看塗裝配置用）

```text
Create a photorealistic aviation photograph in 21:9 ultra-wide format showing an exact side view of a Boeing 787-8 Dreamliner, nose pointing left, taxiing on a runway, shot from far away with a very long telephoto lens so the perspective is almost flat. The whole aircraft fills the width of the frame.

Livery: gloss white front and middle fuselage; gloss black rear fuselage, tail cone and entire vertical stabilizer, divided from the white by one straight diagonal line running from the belly just behind the wing up and back to the top of the fuselage just in front of the tail. On the black fin, a white logo exactly as in Image 1 (three parallel S-curved lines rising to the right, the middle one longest, one small dot after the top line, no circle). On the black rear fuselage, three long white flowing lines in the same style, larger and stretched, rising toward the tail. The text "ASUKA AIR", exactly these letters, in black uppercase geometric sans-serif with wide letter spacing as in Image 2, on the forward upper fuselage just above the passenger windows, starting just behind the first door. White engines with chevron trailing edges, light grey wings. No registration number, no other text or logos, no fern leaf, no spiral motif.

Setting: bright midday sun, green grass beside the runway, low green hills and a blue sky behind. Real photograph, very high detail.
```

## 修正指令

結果不對時，用這些指令接著改：

- 字拼錯：`Fix only the fuselage text so it reads exactly "ASUKA AIR". Keep everything else unchanged.`
- 出現蕨葉或螺旋圖案：`Remove the fern / spiral graphic. Replace it with the three white flowing lines described above. Keep everything else unchanged.`
- 尾翼標誌不對：`Redraw only the tail logo so it matches Image 1 exactly: three parallel S-curved white lines rising to the right, the middle one longest, one small dot after the top line, no circle. Keep everything else unchanged.`
- 黑白分界不對：`Move the black/white boundary: it should be one straight diagonal line from the belly just behind the wing up and back to the top of the fuselage just in front of the tail. Keep everything else unchanged.`
- 機型不像 787：`Make the aircraft an accurate Boeing 787-8: four-pane 787 cockpit windows, raked wingtips without winglets, GEnx engines with chevron nacelle edges. Keep the livery unchanged.`
