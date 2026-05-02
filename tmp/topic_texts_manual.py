"""Hand-authored topic.full_text for the 9 topics that hit Groq's daily token
limit. Content is drawn verbatim (or near-verbatim, with light cleanup of
PDF-extraction artefacts like split words across line breaks) from
chapter.full_text. Used as the AI tutor's RAG context.
"""
from app.db.session import SessionLocal
from app.models.curriculum import Topic


TOPIC_TEXTS: dict[int, str] = {
    # Ch 2 — Diversity In Nature
    13: """The students set out on a nature walk with Dr Raghu and Maniram chacha. The objective of this walk is to experience the beauty and variety of plants and animals in nature. As they walk, they begin exploring the plants and animals around them. Dr Raghu advises the students to notice the variety of smells in the park and emphasises respecting all living creatures and observing them without disturbing. Maniram chacha tells the students to not only observe different plants and animals but also to carefully listen to different sounds. The students come across a variety of plants, including grasses, bushes, and large trees. They also observe a variety of birds sitting on the branches of trees, butterflies moving from flower to flower and monkeys jumping from one tree to another.

The students can hear the chirping of birds. Dr Raghu informs them that each bird has a unique chirp. This is an example of diversity in nature. Dr Raghu requests Maniram chacha to mimic calls of some birds. Maniram chacha mimics different bird calls. The students enthusiastically start copying him.

The variety of plants and animals found in a particular region contributes to the biodiversity of that region. Each member in the biodiversity of a region has a different role to play. For example, trees provide food and shelter to some birds and other animals, animals help in spreading seeds after eating fruits, and so on. This shows that plants and animals are dependent on each other.

Plants have a variety of features such as: tall/short, hard/soft stem; different shapes of leaves and their arrangement on the stem or branches; flowers varying in colour, shape, and scent. Some animals live on land while some others live on trees. Birds live on trees. Fish live in water and some animals like frogs live on land as well as in water. Animals consume a diverse range of foods and exhibit a variety of movements.

Janaki Ammal (1897–1984) was an Indian botanist dedicated to environmental work and helped to document and preserve India's rich plant biodiversity. She played a key role in the 'Save Silent Valley' movement. As the head of the Botanical Survey of India, she initiated programmes to document the plant diversity of India.""",

    # Ch 2 — Seed Structure And Plant Classification
    18: """Is there any relation among the seed of a plant, types of root and leaf venation? Are all seeds similar?

Activity 2.8 (Let us compare): Soak some chickpea and maize seeds in water for two or three days. Remove the seed coat of a chickpea. Now, observe the structure of the chickpea and maize seeds. Are they similar or different?

You would notice that chickpea seeds are split into two parts. Each part is called a cotyledon. Plants that have seeds with two cotyledons are called dicotyledons (dicots). Maize has a single thin cotyledon. Plants with such seeds are called monocotyledons (monocots).

What relation do you observe among leaf venation, root types and the number of cotyledons in seeds of a plant? Dicot plants have reticulate venation and a taproot system, while monocot plants have parallel venation and a fibrous root system.

Generally, plants with reticulate venation have taproots while those with parallel venation have fibrous roots. Chickpea (chana) is another example of a plant with taproots and reticulate venation in leaves. Wheat is an example of a plant with fibrous roots and parallel venation in its leaves.""",

    # Ch 3 — Importance Of Food
    20: """All of us eat food every day. Food is an essential component of our daily life. The Sanskrit saying 'annena jātāni jivanti' means 'food gives life to living beings.'

Have you ever missed a meal? How do you feel when you miss a meal? We feel tired and less energetic when we do not eat for some time. A marathon runner drinks glucose water during and after a race because glucose provides instant energy.

Food is the source from which our body obtains the materials it needs. Food provides energy for performing various activities, supports our growth, helps in repair of body parts, and protects us from diseases.

Dr Poshita, a nutritional expert, explains that 'Health is the Ultimate Wealth.' We should take care of our body to stay healthy. Eating a balanced diet and avoiding junk food contribute towards a healthy body. Good health is essential for leading a happy life.""",

    # Ch 3 — Food Diversity Across Regions
    21: """3.1.1 Food in different regions

Do you think that diversity in food exists in all states of our country?

Activity 3.2 (Let us explore): Find out the types of food traditionally consumed and the crops grown in various states of India. You may refer to books in your library, search the internet, and interact with your friends, family and neighbours to collect information.

Why do we see diversity in traditional food consumed in various states of our country? Some food items are common in many states while some are eaten only in a particular state.

What relation do you find between the traditional food items and the locally grown crops? The traditional food of any state is usually based on the crops grown in that state. India is an agricultural country with diverse soil and climate types. Various crops are grown in its different regions depending on the soil types and climatic conditions.

In various regions of India, the choice of food may vary according to the cultivation of food crops in that particular region, taste preferences, culture, and traditions.

Examples of traditional food in different states of India:
- Punjab grows maize, wheat, chickpea, and pulses; traditional foods include makki di roti, sarson da saag, chhole bhature, parantha, halwa, kheer; beverages include lassi, chhach (buttermilk), milk, and tea.
- Karnataka grows rice, ragi, urad, and coconut; traditional foods include idli, dosa, sambhar, coconut chutney, ragi mudde, palya, rasam, rice; beverages include buttermilk, coffee, and tea.
- Manipur grows rice, bamboo, and soya bean; traditional foods include rice, eromba (chutney), utti (yellow peas and green onion curry), singju, and kangsoi; beverage is black tea.""",

    # Ch 3 — Changes In Cooking Practices
    22: """3.1.2 How have cooking practices changed over time?

You have learnt that food habits vary across states. Our food choices as well as practices of food preparation may differ from one another. Have our food habits and cooking practices changed over time?

Activity 3.3 (Let us interact and find out): Prepare a list of questions for gathering information from elderly people about their food habits and cooking practices. Sample questions include: What kind of food do you still eat and what is new? What are the changes in cooking practices over time? What has caused these changes? Conduct interviews with some elderly people based on the questions prepared.

Cooking practices, also called culinary practices, have changed over time. There is a significant difference between traditional and modern culinary practices. Earlier, most cooking was done using a chulha. Nowadays, most of us cook using a modern gas stove. Earlier, most grinding was done manually using a sil-batta (stone grinder). These days, we use an electrical grinder for ease of grinding.

Why have these culinary practices changed over time? These changes may be due to factors such as technological development, improved transportation and better communication.""",

    # Ch 3 — Components Of Food
    23: """3.2 What are the Components of Food?

Glucose provides instant energy. Glucose is an example of a carbohydrate. Carbohydrates are one of the primary sources of energy in our diet. Cereals like wheat, rice, and maize, vegetables like potato and sweet potato, and fruits like banana, pineapple, and mango are some sources of carbohydrates. Common sugar is also a type of carbohydrate.

Ghee and various kinds of oils are grouped under another kind of food component, which is called fat. Sources of fats can be from plants or animals. Nuts, such as groundnuts, walnuts, coconuts, and almonds, and seeds, such as pumpkin seeds and sunflower seeds, are some sources of fat. Fat is a source of stored energy. Carbohydrates and fats provide us energy for performing various activities. Therefore, they are called energy-giving foods.

Polar bears accumulate a lot of fat under their skin. This fat serves as an energy source. It supports them during their months-long winter sleep (hibernation), enabling them to survive without eating.

Proteins are also an important part of our food. Milk products and pulses are good sources of protein. Sportspersons need proteins in larger quantities to build their muscles. People get proteins from plants as well as animals. Some excellent plant sources of protein are pulses, beans, peas and nuts. Animal sources of protein are milk, paneer, egg, fish and meat. Protein-rich foods help in growth and repair of our body. These are, therefore, called body-building foods.

The right amount of protein must be included in the diet of growing children for their proper growth and development.

Edible mushrooms are good sources of protein. They grow mostly in dark and moist places.

Food components that provide energy, support growth, help repair and protect our body from diseases, and maintain various bodily functions are called nutrients. The major nutrients in our food include carbohydrates, proteins, fats, vitamins and minerals.""",

    # Ch 3 — Protective Nutrients
    24: """Why are we advised to include servings of fruits, vegetables and other plant-based foods in our daily diet?

Case 1: In earlier times, during long voyages, sailors often suffered from bleeding and swollen gums. During a voyage in 1746, Scottish physician James Lind observed that sailors who consumed lemons and oranges recovered from these symptoms. Bleeding and swollen gums are symptoms of a disease called scurvy. Scurvy is caused due to deficiency of Vitamin C. Vitamin C present in citrus fruits like lemons and oranges helps in curing this disease.

Case 2: In the 1960s, Indian scientists found that among the human population in the Himalayan region and the Northern plains of India, symptoms of swelling at the front of the neck were prevalent. As per norms of the Government of India, an effort was made to supplement common salt with iodine for preparing iodised salt. Consumption of iodised salt visibly reduced the above symptoms. These symptoms were due to a deficiency of iodine in the soil of this region resulting in a lack of iodine in the local food and water supply. Swelling at the front of the neck is a symptom of a disease called goitre. Iodised salt is simply common salt mixed with required quantities of salts of iodine.

Vitamins and minerals are two groups of food components that protect our body from various diseases.

Vitamin A keeps eyes and skin healthy. Sources include papaya, carrot, mango, and milk. Deficiency causes loss of vision; symptoms include poor vision, loss of vision in darkness (night blindness), and sometimes complete loss of vision.

Vitamin B1 keeps the heart healthy and supports the body to perform various functions. Sources include legumes, nuts, whole grains, seeds, and milk products. Deficiency causes Beriberi; symptoms include swelling, tingling or burning sensation in feet and hands, and trouble in breathing.

Vitamin C helps the body fight diseases. Sources include amla, guava, green chilli, orange, and lemon. Deficiency causes Scurvy; symptoms include bleeding gums and slow healing of wounds.

Vitamin D helps the body absorb calcium for bone and teeth health. Sources include exposure to sunlight, milk, butter, fish, and eggs. Deficiency causes Rickets, characterised by soft and bent bones.

Calcium keeps bones and teeth healthy. Sources include milk/soya milk, curd, cheese, and paneer. Deficiency causes bone and tooth decay; symptoms include weak bones and tooth decay.

Iodine helps the body perform physical and mental activities. Sources include seaweed, water chestnut (singhada), and iodised salt. Deficiency causes Goitre, with symptoms of swelling at the front of the neck.

Iron is an important component of blood. Sources include green leafy vegetables, beetroot, and pomegranate. Deficiency causes Anaemia; symptoms include weakness and shortness of breath.

Vitamins and minerals are also called protective nutrients. These nutrients protect our body from diseases and keep us healthy. Although vitamins and minerals are required in small amounts, they are essential to keep our body healthy. Some nutrients like vitamin C and others are lost during cooking due to high heat. Washing cut or peeled vegetables and fruits may also result in the loss of some vitamins. However, it is highly recommended that all fruits and vegetables be thoroughly washed before consumption.""",

    # Ch 3 — Testing Food Components
    25: """3.3 How to Test Different Components of Food?

Some nutrients like starch (a type of carbohydrate), fat and protein can be detected using fairly simple tests, while others can be detected only in a well-equipped laboratory.

3.3.1 Test for starch
Activity 3.5 (Let us investigate): Take a small quantity of food items such as a slice of potato, cucumber, bread, some boiled rice, boiled gram, crushed peanuts, oil, butter and crushed coconut. Place a small piece of each item on a separate dish. With the help of a dropper, put 2–3 drops of diluted iodine solution on each food item. Observe if there are any changes in the colour of the food items. Have they turned blue-black? A blue-black colour indicates the presence of starch.

3.3.2 Test for fats
Activity 3.6 (Let us investigate): Take a small part of the food items that you tested for the presence of starch. Place each food item on a separate piece of paper. Wrap the paper around the food and press it. Be careful not to tear the paper. If a food item contains a little water, allow the paper to dry. Does the paper develop an oily patch? If oil or butter is present in the food item, it leaves an oily patch on the paper. Hold the paper against light. Can you see the light faintly shining through this patch? An oily patch on the paper shows that the food item contains fat.

3.3.3 Test for proteins
Activity 3.7 (Let us investigate; demonstrated by the teacher): Take the food items tested in previous activities. Make a paste or powder of the food item using pestle and mortar. Put about half teaspoon of each food item in a separate clean test tube. Add 2–3 teaspoons of water to each test tube and shake them well. Add two drops of copper sulfate solution to each test tube using a dropper. Now, take another dropper and add 10 drops of caustic soda solution to each tube. Shake well and leave the test tubes undisturbed for a few minutes. Did the content of some test tubes turn violet? This violet colour indicates the presence of proteins in the food item.

Precautions: These chemicals are harmful and need to be handled with care. Do not touch any of these chemicals unless asked to do so. If any chemical gets spilled on your body, immediately wash the affected area with water. Do not put any of these chemicals into your mouth, or try to smell them.

Any food which we eat may contain multiple nutrients. Peanuts, for example, show the presence of both proteins and fats.""",

    # Ch 3 — Balanced Diet
    26: """3.4 Balanced Diet

Are nutritional requirements the same for everyone? Do you and your grandparents need the same type or the same amount of nutrients? Requirements of the type and amount of nutrients in a diet may vary according to age, gender, physical activity, health status, lifestyle, and so on.

A diet that has all essential nutrients, roughage, and water in the right amount for proper growth and development of the body is known as a balanced diet.

In addition to the essential nutrients, our body needs dietary fibres and water. Dietary fibres, also known as roughage, do not provide any nutrients to our body. However, they are an essential component of our food. They help our body get rid of undigested food and ensure smooth passage of stools. Roughage in our food is provided mainly by suitable plant products. Green leafy vegetables, fresh fruits, wholegrains, pulses and nuts are good sources of roughage.

Eating food that is locally grown and plant based, to the extent possible, is not only healthy for the body but is also good for our environment and our planet.

Water is also an essential part of our diet. It helps the body absorb nutrients from food. It removes waste from the body through sweat and urine. We should drink sufficient water regularly to keep ourselves healthy.

Some foods have high calories due to high sugar and fat content. Moreover, they contain very low amounts of proteins, minerals, vitamins, and dietary fibres. These foods are called junk foods. These foods include potato wafers, candy bars and carbonated drinks. Consuming these foods frequently is not good as these are not healthy for our body. They make a person obese. Such a person may suffer from several health problems.

Eating a balanced diet and avoiding junk food contribute towards a healthy body. Good health is essential for leading a happy life.

Coluthur Gopalan (1918–2019) initiated nutrition research in India. He analysed more than 500 Indian foods for their nutritional value and recommended an appropriate diet in the Indian context. He led surveys on the nutritional status of the Indian population, identifying widespread deficiencies in protein, energy, and other food components. This led to the implementation of the Mid Day Meal Programme in 2002, now a 'PM POSHAN' initiative, to provide balanced food in the government-run and government-aided schools of our country.

Millets such as jowar, bajra, ragi, and sanwa are native crops of India that can be easily cultivated in different climatic conditions. They are good sources of vitamins, minerals like iron and calcium, and dietary fibres as well — that is why they are also called nutri-cereals. They contribute significantly to a balanced diet required for the normal functioning of our body.""",
}


def main() -> None:
    with SessionLocal() as db:
        wrote = 0
        for tid, text in TOPIC_TEXTS.items():
            t = db.get(Topic, tid)
            if t is None:
                print(f"  topic {tid} not found, skipping")
                continue
            t.full_text = text.strip()
            print(f"  topic {tid:>3} '{t.name}' wrote {len(t.full_text)} chars")
            wrote += 1
        db.commit()
    print(f"\nDone. {wrote} topics updated.")


if __name__ == "__main__":
    main()
