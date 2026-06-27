---
type: "Entrada"
title: "Quis custodiet ipsos custodes?"
description: "Esto no lo escribo desde la teoría. Llevo meses con las manos metidas en dos experimentos que son, cada uno a su manera, una respuesta a un mismo problema."
resource: "https://impermanente.es/2026/05/31/quis-custodiet-ipsos-custodes.html"
tags: []
timestamp: "2026-05-31T12:19:33+02:00"
---

Esto no lo escribo desde la teoría. Llevo meses con las manos metidas en dos experimentos que son, cada uno a su manera, una respuesta a un mismo problema. Uno es una colección de evaluadores epistémicos: piezas pequeñas que miran una conversación y miden cosas como si el sistema se contradice consigo mismo entre un turno y otro, o si una afirmación lleva la atribución que le corresponde. El otro es un marco para diagnosticar por qué un modelo se comporta como se comporta, separando lo que viene del modelo, lo que viene del entorno que lo hospeda y lo que ha moldeado la propia conversación.

Empecé los dos con la fantasía secreta de todo el que construye estas cosas, creyendo que iba a conseguir que la máquina dijera la verdad sobre sí misma. Y los dos me enseñaron lo mismo, por caminos distintos, que es imposible. Lo que aprendí no fue a cerrar el loop sino a dejar de intentarlo y a ser honesto sobre lo que cada pieza puede y no puede hacer.

Cuando un modelo de AI, un LLM, produce una respuesta, ¿puede el mismo modelo decirte si esa respuesta es verdadera? La intuición dice que sí, que es cuestión de afinar. Le colocas un segundo paso, un verificador, le das instrucciones más estrictas, le pides que revise su propio trabajo antes de entregarlo. Suena a control de calidad, algo que es intuitivo en el mundo real. Pero no funciona y no se arregla con más esfuerzo. Y la razón por la que no se arregla la escribieron dos genios hace casi cien años, mucho antes de que existiera nada parecido a un modelo de lenguaje.

El primero fue Tarski que en 1936 demostró algo que al principio parece un juego de palabras y luego te quita el sueño: la verdad de un lenguaje no se puede definir dentro de ese mismo lenguaje. Si quieres hablar de qué frases de un idioma son verdaderas, necesitas salir a un idioma de arriba, un metalenguaje, desde el que mirar el de abajo. Si lo intentas desde dentro, sin salir, chocas con la vieja paradoja del mentiroso: “esta frase es falsa” se muerde la cola y no hay forma de asignarle un valor sin contradicción. La verdad, resulta, es un concepto que solo se puede sostener desde fuera de aquello sobre lo que habla.

Ahora traslada eso a la escena del verificador de AI. Le pides a un modelo que evalúe si lo que acaba de generar es correcto, y para que no haga trampas le dices que se base solo en la información del propio sistema, que no se invente datos, que no recurra a nada externo. Crees que le estás poniendo rigor. Lo que le estás pidiendo, en realidad, es que sea el predicado de verdad de su propio lenguaje. Le estás pidiendo exactamente lo que Tarski demostró que no existe. Y como no puede hacer eso, hace lo único que sí puede hacer desde dentro: comprobar que las piezas encajan entre sí. Que no se contradice. Que la frase de la página tres concuerda con la de la página uno.

Pero eso no es verificar la verdad, solo es verificar la coherencia. Son cosas distintas, y la diferencia importa más de lo que parece, porque un sistema puede ser perfectamente coherente y estar totalmente equivocado. Una mentira bien construida es internamente impecable. De hecho ese es el rasgo de las buenas mentiras.

El segundo genio fue Gödel y lo que aporta es un cuchillo más fino todavía. Su segundo teorema dice que un sistema formal suficientemente potente no puede demostrar su propia consistencia desde dentro. No es que sea difícil. Es que si pudiera, sería inconsistente. La autocertificación no es solo poco fiable sino estructuralmente sospechosa. Un sistema que te asegura que es de fiar usando únicamente sus propias reglas no te ha dado ninguna garantía, te ha dado un reflejo de sí mismo. Cuando un modelo te dice “he revisado mi respuesta y es correcta”, está haciendo precisamente ese movimiento. Te ofrece una consistencia que él mismo produce sobre un material que él mismo generó. El loop se cierra sobre el vacío.

¿Y mis dos experimentos?

El primer cacharro acabó teniendo una frase escrita en su propia documentación que al principio me dolió poner y ahora me parece lo único valioso de todo el proyecto: esto comprueba señales, no verdad; para lo que de verdad importa, busca una fuente externa o un humano. Es una rendición, leída de una manera. Es la única honestidad posible, leída de la otra. Un evaluador que mide coherencia y promete coherencia vale más que uno que mide coherencia y promete verdad, aunque el segundo se venda mejor.

El segundo cacharro aprendió la lección por el lado contrario: en vez de pedirle al modelo que certificara su propia consistencia, que es justo lo que Gödel dice que no sirve, construí la palanca por fuera. Un registro de lo que el modelo fue diciendo a lo largo de una sesión entera, acumulado, que vuelve cara la transparencia fingida porque obliga a sostener la misma historia durante demasiado rato. La verdad ahí sale barata, porque solo tiene que apuntar hacia atrás, hacia lo que ya se dijo. La actuación sale cara, porque tiene que ir reescribiendo el pasado sobre la marcha, y las costuras se notan. Me inspiré en CIRIS, un modelo pensado en ser seguro desde el inicio.

Ninguno de los dos resuelve el problema de fondo, porque ya vimos que no pueden.

# Citations

[1] [Original en impermanente.es](https://impermanente.es/2026/05/31/quis-custodiet-ipsos-custodes.html)
