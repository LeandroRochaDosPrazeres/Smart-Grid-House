#include <Servo.h>   // Biblioteca para controlar servomotores

// ======================
// SERVO HORIZONTAL
// ======================
Servo horizontal;            // Cria objeto do servo horizontal
int servohori = 180;        // Posição inicial do servo horizontal
int servohoriLimitHigh = 175; // Limite máximo de giro
int servohoriLimitLow = 5;    // Limite mínimo de giro

// ======================
// SERVO VERTICAL
// ======================
Servo vertical;             // Cria objeto do servo vertical
int servovert = 45;         // Posição inicial do servo vertical
int servovertLimitHigh = 100; // Limite máximo
int servovertLimitLow = 1;    // Limite mínimo

// ======================
// PINOS DOS LDRs
// ======================
// Sensores de luz (LDR) ligados nas entradas analógicas
int ldrlt = A0; // Superior esquerdo
int ldrrt = A3; // Superior direito
int ldrld = A1; // Inferior esquerdo
int ldrrd = A2; // Inferior direito

// ======================
// CONFIGURAÇÃO INICIAL
// ======================
void setup() {

  horizontal.attach(2); // Servo horizontal ligado no pino 2
  vertical.attach(13);  // Servo vertical ligado no pino 13

  horizontal.write(180); // Define posição inicial horizontal
  vertical.write(45);    // Define posição inicial vertical

  delay(2500); // Espera 2,5 segundos
}

// ======================
// LOOP PRINCIPAL
// ======================
void loop() {

  // Leitura dos sensores LDR
  int lt = analogRead(ldrlt); // Superior esquerdo
  int rt = analogRead(ldrrt); // Superior direito
  int ld = analogRead(ldrld); // Inferior esquerdo
  int rd = analogRead(ldrrd); // Inferior direito

  int dtime = 10; // Tempo entre movimentos
  int tol = 90;   // Tolerância para evitar trepidação

  // ======================
  // MÉDIAS DOS LADOS
  // ======================

  int avt = (lt + rt) / 2; // Média parte superior
  int avd = (ld + rd) / 2; // Média parte inferior
  int avl = (lt + ld) / 2; // Média lado esquerdo
  int avr = (rt + rd) / 2; // Média lado direito

  // Diferença entre sensores
  int dvert = avt - avd;   // Diferença vertical
  int dhoriz = avl - avr;  // Diferença horizontal

  // ======================
  // CONTROLE VERTICAL
  // ======================

  if (abs(dvert) > tol) { 

    if (avt > avd) {      // Mais luz em cima
      servovert++;        // Sobe o servo
      if (servovert > servovertLimitHigh)
        servovert = servovertLimitHigh;

    } else {              // Mais luz embaixo
      servovert--;        // Desce o servo
      if (servovert < servovertLimitLow)
        servovert = servovertLimitLow;
    }

    vertical.write(servovert); // Move servo vertical
  }

  // ======================
  // CONTROLE HORIZONTAL
  // ======================
  if (abs(dhoriz) > tol) { 

    if (avl > avr) {       // Mais luz na esquerda
      servohori--;         // Move para esquerda
      if (servohori < servohoriLimitLow)
        servohori = servohoriLimitLow;

    } else {               // Mais luz na direita
      servohori++;         // Move para direita
      if (servohori > servohoriLimitHigh)
        servohori = servohoriLimitHigh;
    }

    horizontal.write(servohori); // Move servo horizontal
  }

  delay(dtime); 
}